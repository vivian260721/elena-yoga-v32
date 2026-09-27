import copy
import json
from pathlib import Path
import random
import tempfile
import unittest
from unittest.mock import patch

from models.feedback_loader import load_feedback
from utils.json_feedback import JsonFeedback, STATES
from utils.pose_comparison import PoseComparison


class JsonFeedbackTests(unittest.TestCase):
    def setUp(self):
        self.generator = JsonFeedback(rng=random.Random(42))
        self.comparator = PoseComparison()

    def test_all_40_entries_and_reference_snapshots(self):
        poses = self.generator.bank["poses"]
        self.assertEqual(sum(map(len, poses.values())), 40)
        for pose, entries in poses.items():
            for name, entry in entries.items():
                self.assertEqual(entry["reference_deg"], self.comparator.reference_angles[pose][name])
                for state in STATES:
                    self.assertGreaterEqual(len(entry[state]), 1)

    def test_every_pose_joint_and_direction_uses_its_own_bank(self):
        for pose, entries in self.generator.bank["poses"].items():
            for name, entry in entries.items():
                for state, actual in (("too_low", 30), ("too_high", 150)):
                    with self.subTest(pose=pose, name=name, state=state):
                        comparison = {"is_standard": False, "angles": {name: {
                            "actual_deg": actual, "reference_deg": 90, "within_tolerance": False}}}
                        with patch.object(self.generator.rng, "choice", side_effect=lambda values: values[-1]) as choose:
                            _, suggestions = self.generator.generate(pose, comparison)
                        choose.assert_called_once_with(entry[state])
                        self.assertIn("參考 90.0°", suggestions[0])
                        self.assertIn("增加 60.0°" if state == "too_low" else "減少 60.0°", suggestions[0])

    def test_swapped_reference_and_priority(self):
        pose = "戰士二式"
        targets = self.comparator.reference_angles[pose]
        measured = {name: targets[("R" if name.startswith("L") else "L") + name[1:]] for name in targets}
        comparison = self.comparator.evaluate_angles(pose, measured)
        self.assertTrue(comparison["is_standard"])
        comparison["angles"]["L_knee_angle"].update(actual_deg=20, within_tolerance=False)
        comparison["is_standard"] = False
        _, suggestions = self.generator.generate(pose, comparison)
        target = comparison["angles"]["L_knee_angle"]["reference_deg"]
        self.assertEqual(len(suggestions), 1)
        self.assertIn(f"參考 {target:.1f}°", suggestions[0])

    def test_missing_joints_and_downdog_side_view(self):
        for pose in ("下犬式", "平板式"):
            measured = dict(self.comparator.reference_angles[pose])
            measured.update({name: None for name in measured if name.startswith("R")})
            comparison = self.comparator.evaluate_angles(pose, measured)
            feedback, suggestions = self.generator.generate(pose, comparison)
            if pose == "下犬式":
                self.assertTrue(comparison["is_standard"])
                self.assertIn("可見側", feedback)
                self.assertNotIn("入鏡", "".join(suggestions))
            else:
                self.assertIsNone(comparison["is_standard"])
                self.assertEqual(len(suggestions), 4)
                self.assertNotIn("°", "".join(suggestions))

    def test_randomness_only_changes_wording(self):
        comparison = {"is_standard": False, "angles": {"L_knee_angle": {
            "actual_deg": 30, "reference_deg": 90, "within_tolerance": False}}}
        before = copy.deepcopy(comparison)
        outputs = {self.generator.generate("樹式", comparison)[1][0] for _ in range(30)}
        self.assertEqual(len(outputs), 3)
        self.assertEqual(comparison, before)

    def test_invalid_bank_rejected(self):
        for invalid in ([], [""], ["{unknown}", "valid"]):
            bank = copy.deepcopy(self.generator.bank)
            bank["poses"]["樹式"]["L_knee_angle"]["too_low"] = invalid
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "bad.json"
                path.write_text(json.dumps(bank), encoding="utf-8")
                with self.assertRaises(ValueError):
                    JsonFeedback(path)

    def test_largest_error_first_and_passing_joints_omitted(self):
        comparison = {"is_standard": False, "angles": {
            "L_knee_angle": {"actual_deg": 60, "reference_deg": 90, "within_tolerance": False},
            "R_hip_angle": {"actual_deg": 150, "reference_deg": 90, "within_tolerance": False},
            "L_elbow_angle": {"actual_deg": 90, "reference_deg": 90, "within_tolerance": True},
        }}
        _, suggestions = self.generator.generate("平板式", comparison)
        self.assertEqual(len(suggestions), 2)
        self.assertIn("減少 60.0°", suggestions[0])
        self.assertIn("增加 30.0°", suggestions[1])

    def test_loader_does_not_import_llm_packages(self):
        import builtins
        original = builtins.__import__
        def guarded(name, *args, **kwargs):
            if name in ("torch", "transformers"):
                raise AssertionError(f"Unexpected model import: {name}")
            return original(name, *args, **kwargs)
        with patch("builtins.__import__", side_effect=guarded):
            self.assertIsInstance(load_feedback(), JsonFeedback)


if __name__ == "__main__":
    unittest.main()
