"""Validated phrase bank; numerical decisions remain in PoseComparison."""
import json
import math
import random
from pathlib import Path
from string import Formatter

from utils.angle_feedback import JOINT_NAMES, build_angle_feedback
from utils.pose_translator import PoseTranslator

ROOT = Path(__file__).resolve().parents[1]
STATES = ("too_low", "too_high", "within_tolerance", "unavailable")


class JsonFeedback:
    def __init__(self, path="data/pose_feedback_fix.json", rng=None):
        path = Path(path)
        if not path.is_absolute():
            path = ROOT / path
        with path.open(encoding="utf-8-sig") as stream:
            self.bank = json.load(stream)
        self.rng = rng if rng is not None else random
        self._validate()

    def _validate(self):
        if self.bank.get("schema_version") != 1:
            raise ValueError("Feedback JSON: unsupported schema_version")
        poses = self.bank.get("poses", {})
        if set(poses) != set(PoseTranslator.get_pose_names_zh()):
            raise ValueError("Feedback JSON must contain exactly the five supported poses")
        for pose, entries in poses.items():
            if set(entries) != set(JOINT_NAMES):
                raise ValueError(f"Feedback JSON: {pose} must contain all eight angles")
            for name, entry in entries.items():
                value = entry.get("reference_deg")
                if (type(value) not in (int, float) or not math.isfinite(value)
                        or not 0 <= value <= 180):
                    raise ValueError(f"Feedback JSON: invalid reference for {pose}/{name}")
                for state in STATES:
                    phrases = entry.get(state)
                    if (not isinstance(phrases, list) or len(phrases) < 1
                            or any(not isinstance(p, str) or not p.strip() for p in phrases)):
                        raise ValueError(f"Feedback JSON: {pose}/{name}/{state} needs at least one phrase")
                    for phrase in phrases:
                        for _, field, spec, conversion in Formatter().parse(phrase):
                            if field is not None and (field not in {"pose", "joint"} or spec or conversion):
                                raise ValueError(f"Feedback JSON: unsupported placeholder {field}")

    def generate(self, pose, comparison, **kwargs):
        pose = PoseTranslator.translate_to_chinese(pose) or pose
        entries = self.bank["poses"][pose]
        comparison = dict(comparison, pose_name_zh=pose)
        # Preserve established status wording and side-view assessment semantics.
        feedback, fallback = build_angle_feedback(comparison, include_priority=False)
        corrections, passed, unavailable = [], [], []
        for name, angle in comparison["angles"].items():
            status = angle["within_tolerance"]
            if status is None:
                state = "unavailable"
            elif status:
                state = "within_tolerance"
            else:
                state = "too_low" if angle["actual_deg"] < angle["reference_deg"] else "too_high"
            phrase = self.rng.choice(entries[name][state]).format(pose=pose, joint=JOINT_NAMES[name])
            if status is None:
                unavailable.append(phrase)
            elif status:
                passed.append(phrase)
            else:
                actual, target = angle["actual_deg"], angle["reference_deg"]
                amount = abs(target - actual)
                direction = "增加" if state == "too_low" else "減少"
                phrase += f"（目前 {actual:.1f}°，參考 {target:.1f}°，角度約需{direction} {amount:.1f}°）。"
                corrections.append((amount, phrase))
        corrections.sort(key=lambda item: item[0], reverse=True)
        suggestions = [phrase for _, phrase in corrections]
        if pose != "下犬式":
            suggestions.extend(unavailable)
        if comparison["is_standard"] is True:
            suggestions = [self.rng.choice(passed)] if passed else fallback
        elif pose == "下犬式" and comparison["is_standard"] is None:
            suggestions = fallback
        if corrections:
            feedback += f"有 {len(corrections)} 個部位需要調整，先從「{suggestions[0].split('（')[0]}」開始。"
        return feedback, suggestions
