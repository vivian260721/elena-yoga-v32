import unittest

from utils.angle_feedback import build_angle_feedback
from utils.pose_comparison import PoseComparison


class DowndogFeedbackTests(unittest.TestCase):
    def setUp(self):
        self.comparison = PoseComparison()
        self.pose = "下犬式"
        self.reference = self.comparison.reference_angles[self.pose]

    def evaluate(self, measured):
        result = self.comparison.evaluate_angles(self.pose, measured)
        feedback, suggestions = build_angle_feedback(result)
        text = " ".join([result["overall_assessment"], feedback, *suggestions])
        self.assertNotIn("無法完整判定：部分關節不可見或無法計算角度", text)
        self.assertNotIn("目前無法判定是否符合標準：部分關節不清楚", text)
        return result, text

    def test_either_complete_side_can_pass(self):
        for side in ("L", "R"):
            with self.subTest(side=side):
                measured = {name: value for name, value in self.reference.items()
                            if name.startswith(side)}
                result, text = self.evaluate(measured)
                self.assertIs(result["is_standard"], True)
                self.assertEqual(len(result["unavailable_angles"]), 4)
                self.assertIn("可見側", text)
                self.assertNotIn("八個", text)
                self.assertNotIn("重新拍攝", text)

    def test_visible_error_still_fails(self):
        measured = {name: value for name, value in self.reference.items()
                    if name.startswith("L")}
        measured["L_knee_angle"] = 0 if measured["L_knee_angle"] > 90 else 180
        result, text = self.evaluate(measured)
        self.assertIs(result["is_standard"], False)
        self.assertIn("左膝", text)
        self.assertNotIn("重新拍攝", text)

    def test_incomplete_or_absent_side_does_not_pass(self):
        for measured in ({}, {"L_hip_angle": self.reference["L_hip_angle"]}):
            result, text = self.evaluate(measured)
            self.assertIsNone(result["is_standard"])
            self.assertIn("同一側", text)

    def test_other_poses_still_require_both_sides(self):
        for pose, reference in self.comparison.reference_angles.items():
            if pose == self.pose:
                continue
            measured = {name: value for name, value in reference.items()
                        if name.startswith("L")}
            result = self.comparison.evaluate_angles(pose, measured)
            self.assertIsNone(result["is_standard"])
            self.assertIn("無法完整判定", result["overall_assessment"])
