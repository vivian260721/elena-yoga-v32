"""Build 77 features: 23 xyz landmarks, then eight XYZ joint angles."""
import numpy as np


class FeatureExtractor:
    KEYPOINT_INDICES = (0, *range(11, 33))
    ANGLE_NAMES = (
        "left_elbow_angle_deg", "right_elbow_angle_deg",
        "left_shoulder_angle_deg", "right_shoulder_angle_deg",
        "left_hip_angle_deg", "right_hip_angle_deg",
        "left_knee_angle_deg", "right_knee_angle_deg",
    )

    @classmethod
    def feature_names(cls):
        return [f"kp_{i}_{axis}" for i in cls.KEYPOINT_INDICES for axis in "xyz"] + list(cls.ANGLE_NAMES)

    def extract_features(self, landmarks: np.ndarray) -> np.ndarray:
        points = np.asarray(landmarks, dtype=np.float64)
        if points.shape != (33, 3) or not np.isfinite(points).all():
            raise ValueError("Expected finite landmarks with shape (33, 3)")
        # Classification was trained on angles between XYZ vectors, in degrees.
        joints = ((11, 13, 15), (12, 14, 16),
                  (13, 11, 23), (14, 12, 24), (11, 23, 25),
                  (12, 24, 26), (23, 25, 27), (24, 26, 28))
        angles = [self._calculate_angle(points[a], points[b], points[c]) for a, b, c in joints]
        return np.concatenate((points[list(self.KEYPOINT_INDICES)].ravel(), angles))

    @staticmethod
    def _calculate_angle(p1, p2, p3) -> float:
        v1, v2 = p1 - p2, p3 - p2
        denominator = np.linalg.norm(v1) * np.linalg.norm(v2)
        if denominator <= np.finfo(float).eps:
            return 0.0
        return float(np.degrees(np.arccos(np.clip(np.dot(v1, v2) / denominator, -1, 1))))
