import unittest
from utils.angle_feedback import build_angle_feedback, JOINT_NAMES


def result(name, actual, target, passed=False):
    return {"is_standard": passed, "overall_assessment": "角度評估",
            "angles": {name: {"actual_deg": actual, "reference_deg": target,
                              "within_tolerance": passed}}}


class AngleFeedbackTests(unittest.TestCase):
    def test_feedback_states_status_and_first_action(self):
        feedback, suggestions = build_angle_feedback(result('L_knee_angle', 120, 175))
        self.assertIn('尚未符合標準', feedback)
        self.assertIn('左腿再伸直一些', feedback)
        self.assertIn('左腿再伸直一些', suggestions[0])
        feedback, _ = build_angle_feedback(result('L_knee_angle', 175, 175, True))
        self.assertIn('符合標準', feedback)
        feedback, _ = build_angle_feedback(result('L_knee_angle', None, 175, None))
        self.assertIn('無法判定是否符合標準', feedback)

    def test_increase_and_decrease_for_all_joints(self):
        for name in JOINT_NAMES:
            for actual, target in ((60, 90), (120, 90)):
                with self.subTest(name=name, actual=actual):
                    _, suggestions = build_angle_feedback(result(name, actual, target))
                    text = suggestions[0]
                    self.assertIn("30.0°", text)
                    self.assertIn(f"目前 {actual:.1f}°", text)
                    self.assertIn("參考 90.0°", text)
                    if 'shoulder' in name:
                        self.assertIn('張開' if actual < target else '收回', text)
                    elif 'hip' in name:
                        self.assertIn('增加' if actual < target else '減少', text)
                    else:
                        self.assertIn('伸直' if actual < target else '彎曲', text)

    def test_passed_angles_are_not_corrected(self):
        _, suggestions = build_angle_feedback(result('L_knee_angle', 75, 90, True))
        self.assertEqual(len(suggestions), 1)
        self.assertIn('無需額外調整', suggestions[0])

    def test_unknown_angles_have_no_invented_degrees(self):
        _, suggestions = build_angle_feedback(result('L_knee_angle', None, 90, None))
        self.assertIn('左膝', suggestions[0])
        self.assertNotIn('°', suggestions[0])

    def test_largest_deviation_first_and_passed_omitted(self):
        comparison = result('L_knee_angle', 70, 90)
        comparison['angles'].update(result('R_hip_angle', 130, 90)['angles'])
        comparison['angles'].update(result('L_elbow_angle', 90, 90, True)['angles'])
        _, suggestions = build_angle_feedback(comparison)
        self.assertEqual(len(suggestions), 2)
        self.assertIn('右髖', suggestions[0])
        self.assertIn('左膝', suggestions[1])
