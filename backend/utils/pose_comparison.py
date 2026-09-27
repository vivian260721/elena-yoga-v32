"""
姿勢比較器 - 將用戶姿勢與標準姿勢進行比較
"""

import numpy as np
import csv
from pathlib import Path
from typing import Dict
from utils.pose_translator import PoseTranslator
from utils.normalizer import Normalizer
from config.settings import REFERENCE_POSES_PATH


class PoseComparison:
    """
    姿勢比較
    - 加載標準姿勢數據
    - 比較用戶姿勢與標準姿勢
    - 依 CSV 八個角度與 容許差（髖 ±30°、其餘 ±20°） 容許差判定標準動作
    """
    
    ANGLE_JOINTS = {
        "L_elbow_angle": (11, 13, 15), "R_elbow_angle": (12, 14, 16),
        "L_shoulder_angle": (13, 11, 23), "R_shoulder_angle": (14, 12, 24),
        "L_hip_angle": (11, 23, 25), "R_hip_angle": (12, 24, 26),
        "L_knee_angle": (23, 25, 27), "R_knee_angle": (24, 26, 28),
    }
    ANGLE_TOLERANCE_DEG = 20.0
    HIP_ANGLE_TOLERANCE_DEG = 30.0
    REVERSIBLE_POSES = frozenset({"樹式", "戰士二式"})
    # Reference CSV stores angles rounded to one decimal place.
    REFERENCE_ROUNDING_TOLERANCE_DEG = 0.050001

    def __init__(self, reference_path=REFERENCE_POSES_PATH):
        """初始化姿勢比較器"""
        self.reference_poses = {}  # 標準姿勢參考數據
        self.reference_angles = {}
        self.reference_path = Path(reference_path)
        if not self.reference_path.is_absolute():
            self.reference_path = Path(__file__).resolve().parents[1] / self.reference_path
        self._load_reference_poses()
    
    def _load_reference_poses(self):
        """加載標準姿勢參考數據"""
        columns = [f"lm_{i}_{axis}" for i in range(33) for axis in "xyz"]
        normalizer = Normalizer()
        with self.reference_path.open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            missing = set(columns + ["pose_class"] + list(self.ANGLE_JOINTS)) - set(reader.fieldnames or [])
            if missing:
                raise ValueError(f"Reference CSV missing columns: {', '.join(sorted(missing))}")
            for line, row in enumerate(reader, 2):
                label = (row["pose_class"] or "").strip()
                pose = PoseTranslator.translate_to_chinese(label) or label
                if not PoseTranslator.is_valid_pose_zh(pose):
                    raise ValueError(f"Reference CSV row {line}: unknown pose {label!r}")
                if pose in self.reference_poses:
                    raise ValueError(f"Reference CSV row {line}: duplicate reference for {pose}")
                try:
                    points = np.array([float(row[c]) for c in columns]).reshape(33, 3)
                except (ValueError, TypeError) as exc:
                    raise ValueError(f"Reference CSV row {line}: invalid landmark coordinates") from exc
                if not np.isfinite(points).all():
                    raise ValueError(f"Reference CSV row {line}: non-finite landmark coordinates")
                # CSV has no visibility; reference points are assumed reliable.
                normalized, center = normalizer.normalize(points)
                if center == "none":
                    raise ValueError(f"Reference CSV row {line}: degenerate pose")
                self.reference_poses[pose] = normalized
                try:
                    angles = {name: float(row[name]) for name in self.ANGLE_JOINTS}
                except (ValueError, TypeError) as exc:
                    raise ValueError(f"Reference CSV row {line}: invalid angles") from exc
                if any(not np.isfinite(value) or not 0 <= value <= 180 for value in angles.values()):
                    raise ValueError(f"Reference CSV row {line}: angles must be finite and within 0..180 degrees")
                recalculated = self.measure_angles(points)
                for name, target in angles.items():
                    actual = recalculated[name]
                    if actual is None or abs(actual - target) > self.REFERENCE_ROUNDING_TOLERANCE_DEG:
                        raise ValueError(
                            f"Reference CSV row {line}: {name} does not match "
                            f"normalized image x/y angle (stored={target}, calculated={actual})"
                        )
                self.reference_angles[pose] = angles
        missing_poses = set(PoseTranslator.get_pose_names_zh()) - self.reference_poses.keys()
        if missing_poses:
            raise ValueError(f"Reference CSV missing poses: {', '.join(sorted(missing_poses))}")
    
    def compare(self, pose_name: str, landmarks: np.ndarray, visibility=None) -> Dict:
        """
        比較用戶姿勢與標準姿勢
        
        Args:
            pose_name: 預測的姿勢名稱 (中文)
            landmarks: 原始 image landmarks (33, 3)，搭配 visibility
            
        Returns:
            Dict: 八項角度差、is_standard 與判定描述
        """
        landmarks = np.asarray(landmarks)
        if landmarks.shape != (33, 3) or not np.isfinite(landmarks).all():
            raise ValueError("Expected finite normalized landmarks with shape (33, 3)")
        pose_name = PoseTranslator.translate_to_chinese(pose_name) or pose_name
        return self.compare_angles(pose_name, landmarks, visibility)

    def compare_angles(self, pose_name, landmarks, visibility=None):
        """CSV image-plane angles: hips ±30 degrees, others ±20 degrees; classifier confidence is not used."""
        if pose_name not in self.reference_angles:
            raise ValueError(f"Reference pose '{pose_name}' not found")
        return self.evaluate_angles(pose_name, self.measure_angles(landmarks, visibility))

    @classmethod
    def measure_angles(cls, landmarks, visibility=None):
        """Unsigned 0..180 degree angles in normalized image x/y, matching the CSV.

        Do not add z or independently rescale x/y to pixels: either changes
        the metric used by the reference dataset.
        """
        landmarks = np.asarray(landmarks, dtype=float)
        if landmarks.shape != (33, 3) or not np.isfinite(landmarks).all():
            raise ValueError("Expected finite image landmarks with shape (33, 3)")
        if visibility is None:
            visibility = np.ones(33)
        visibility = np.asarray(visibility)
        if visibility.shape != (33,) or not np.isfinite(visibility).all():
            raise ValueError("Expected finite visibility with shape (33,)")
        measured = {}
        for name, indices in cls.ANGLE_JOINTS.items():
            a, b, c = landmarks[list(indices), :2].astype(float)
            v1, v2 = a - b, c - b
            denominator = np.linalg.norm(v1) * np.linalg.norm(v2)
            if np.any(visibility[list(indices)] < Normalizer.CONFIDENCE_THRESHOLD) or denominator <= np.finfo(float).eps:
                measured[name] = None
            else:
                measured[name] = float(np.degrees(np.arccos(np.clip(np.dot(v1, v2) / denominator, -1, 1))))
        return measured

    def evaluate_angles(self, pose_name, measured):
        reference = self.reference_angles[pose_name]
        reference_mirrored = False
        if pose_name in self.REVERSIBLE_POSES:
            swapped = {
                name: reference[("R" if name.startswith("L_") else "L") + name[1:]]
                for name in reference
            }

            def score(candidate):
                # Select one whole reference. Never swap measured joint labels
                # or choose a different orientation for each joint.
                failed = 0
                error = 0.0
                for name, target in candidate.items():
                    value = measured.get(name)
                    if value is None or not np.isfinite(value) or not 0 <= value <= 180:
                        continue
                    tolerance = (self.HIP_ANGLE_TOLERANCE_DEG if "hip" in name
                                 else self.ANGLE_TOLERANCE_DEG)
                    difference = abs(value - target)
                    failed += difference > tolerance + 1e-9
                    error += difference / tolerance
                return failed, error

            # Prefer a passing reference, then fewer failures and lower error.
            # Ties (including no visible joints) retain the original reference.
            chosen = min(((reference, False), (swapped, True)), key=lambda item: score(item[0]))
            reference, reference_mirrored = chosen
        results = {}
        for name, target in reference.items():
            value = measured.get(name)
            valid = value is not None and np.isfinite(value) and 0 <= value <= 180
            delta = float(value - target) if valid else None
            tolerance = self.HIP_ANGLE_TOLERANCE_DEG if name in ("L_hip_angle", "R_hip_angle") else self.ANGLE_TOLERANCE_DEG
            results[name] = {
                "reference_deg": target, "actual_deg": float(value) if valid else None,
                "difference_deg": delta, "tolerance_deg": tolerance,
                "within_tolerance": bool(abs(delta) <= tolerance + 1e-9) if valid else None,
            }
        failed = [name for name, result in results.items() if result["within_tolerance"] is False]
        unavailable = [name for name, result in results.items() if result["within_tolerance"] is None]
        standard = False if failed else (None if unavailable else True)
        if pose_name == "下犬式":
            # A side view may hide the far side. Require one complete side
            # before passing, while preserving failures on any visible joint.
            complete_side = any(
                all(results[f"{side}_{joint}_angle"]["within_tolerance"] is not None
                    for joint in ("elbow", "shoulder", "hip", "knee"))
                for side in ("L", "R")
            )
            standard = False if failed else (True if complete_side else None)
        assessment = "符合標準：八個角度均在參考值 容許差（髖 ±30°、其餘 ±20°） 內" if standard is True else (
            "未符合標準：有角度超出參考值 容許差（髖 ±30°、其餘 ±20°）" if standard is False else "無法完整判定：部分關節不可見或無法計算角度")
        if pose_name == "下犬式":
            assessment = (
                "符合標準：下犬式可見側角度均在容許差內（髖 ±30°、其餘 ±20°）"
                if standard is True else
                "未符合標準：下犬式可見關節有角度超出容許差（髖 ±30°、其餘 ±20°）"
                if standard is False else
                "下犬式側面評估：請讓同一側的肩、肘、腕、髖、膝、踝完整入鏡。"
            )
        return {
            "pose_name_zh": pose_name,
            "pose_name_en": PoseTranslator.translate_to_english(pose_name),
            "reference_mirrored": reference_mirrored,
            "tolerance_deg": self.ANGLE_TOLERANCE_DEG,
            "is_standard": standard, "angles": results,
            "problematic_points": failed, "unavailable_angles": unavailable,
            "overall_assessment": assessment,
        }

