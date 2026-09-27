import csv
from pathlib import Path
import tempfile
import unittest
import numpy as np
from utils.pose_comparison import PoseComparison
from utils.normalizer import Normalizer
from utils.pose_translator import PoseTranslator
from utils.angle_feedback import build_angle_feedback


class ReferenceTests(unittest.TestCase):
    def setUp(self):
        self.path = Path(__file__).resolve().parents[1] / 'utils/yoga_5poses_mediapipe_dataset_complete.csv'
        with self.path.open(encoding='utf-8-sig', newline='') as stream:
            reader = csv.DictReader(stream)
            self.fields = reader.fieldnames
            self.rows = list(reader)

    def write_csv(self, directory, fields, rows):
        path = Path(directory) / 'references.csv'
        with path.open('w', encoding='utf-8-sig', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=fields, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(rows)
        return path

    def test_every_pose_matches_itself_and_english_alias(self):
        comparison = PoseComparison(self.path)
        self.assertEqual(len(comparison.reference_poses), 5)
        for row in self.rows:
            points = np.array([[float(row[f'lm_{i}_{axis}']) for axis in 'xyz'] for i in range(33)])
            normalized, _ = Normalizer().normalize(points)
            for name in (row['pose_class'], PoseTranslator.translate_to_english(row['pose_class'])):
                result = comparison.compare(name, normalized)
                self.assertNotIn('error', result)
                self.assertTrue(result['is_standard'], result)
                self.assertEqual(len(result['angles']), 8)

    def test_shuffled_columns_do_not_change_mapping(self):
        expected = PoseComparison(self.path)
        with tempfile.TemporaryDirectory() as directory:
            actual = PoseComparison(self.write_csv(directory, list(reversed(self.fields)), self.rows))
        for pose in expected.reference_poses:
            np.testing.assert_array_equal(expected.reference_poses[pose], actual.reference_poses[pose])

    def test_reversed_tree_and_warrior_landmarks_pass(self):
        comparison = PoseComparison(self.path)
        for pose in comparison.REVERSIBLE_POSES:
            with self.subTest(pose=pose):
                points = comparison.reference_poses[pose].copy()
                for left in range(11, 33, 2):
                    points[[left, left + 1]] = points[[left + 1, left]]
                points[:, 0] *= -1
                result = comparison.compare(pose, points)
                self.assertTrue(result['is_standard'])
                for name, angle in result['angles'].items():
                    opposite = ('R' if name[0] == 'L' else 'L') + name[1:]
                    self.assertEqual(angle['reference_deg'], comparison.reference_angles[pose][opposite])

    def test_reversed_feedback_keeps_actual_body_side(self):
        comparison = PoseComparison(self.path)
        for pose in comparison.REVERSIBLE_POSES:
            ref = comparison.reference_angles[pose]
            measured = {name: ref[('R' if name[0] == 'L' else 'L') + name[1:]] for name in ref}
            name = next(name for name in ('L_knee_angle', 'R_knee_angle') if measured[name] > 170)
            measured[name] -= 25
            result = comparison.evaluate_angles(pose, measured)
            self.assertFalse(result['is_standard'])
            self.assertEqual(result['problematic_points'], [name])
            _, suggestions = build_angle_feedback(result)
            self.assertIn(('左' if name[0] == 'L' else '右') + '腿再伸直', suggestions[0])

    def test_cannot_mix_reference_sides_to_pass_both_straight_knees(self):
        comparison = PoseComparison(self.path)
        for pose in comparison.REVERSIBLE_POSES:
            measured = dict(comparison.reference_angles[pose])
            measured['L_knee_angle'] = measured['R_knee_angle'] = 179.0
            self.assertFalse(comparison.evaluate_angles(pose, measured)['is_standard'])

    def test_reversed_pose_missing_joint_remains_unknown(self):
        comparison = PoseComparison(self.path)
        for pose in comparison.REVERSIBLE_POSES:
            ref = comparison.reference_angles[pose]
            measured = {name: ref[('R' if name[0] == 'L' else 'L') + name[1:]] for name in ref}
            measured['L_elbow_angle'] = None
            result = comparison.evaluate_angles(pose, measured)
            self.assertIsNone(result['is_standard'])
            self.assertEqual(result['unavailable_angles'], ['L_elbow_angle'])

    def test_all_reference_angles_match_xy_within_csv_rounding(self):
        for row in self.rows:
            points = np.array([[float(row[f'lm_{i}_{axis}']) for axis in 'xyz'] for i in range(33)])
            measured = PoseComparison.measure_angles(points)
            for name, value in measured.items():
                with self.subTest(pose=row['pose_class'], angle=name):
                    self.assertAlmostEqual(value, float(row[name]), delta=0.050001)
            points[:, 2] += np.arange(33) * 10
            self.assertEqual(measured, PoseComparison.measure_angles(points))

    def test_inconsistent_reference_angle_rejected(self):
        rows = [{**self.rows[0], 'L_elbow_angle': '150.0'}] + self.rows[1:]
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, 'L_elbow_angle does not match'):
                PoseComparison(self.write_csv(directory, self.fields, rows))

    def test_degenerate_joint_is_unavailable(self):
        points = np.zeros((33, 3))
        self.assertTrue(all(value is None for value in PoseComparison.measure_angles(points).values()))

    def test_invalid_schema_or_reference_rejected(self):
        cases = [
            ([f for f in self.fields if f != 'lm_0_x'], self.rows),
            (self.fields, self.rows[:-1]),
            (self.fields, self.rows + [self.rows[0]]),
            (self.fields, [{**self.rows[0], 'lm_0_x': 'nan'}] + self.rows[1:]),
            (self.fields, [{**self.rows[0], 'L_elbow_angle': 'nan'}] + self.rows[1:]),
        ]
        with tempfile.TemporaryDirectory() as directory:
            for fields, rows in cases:
                with self.subTest(fields=len(fields), rows=len(rows)):
                    path = self.write_csv(directory, fields, rows)
                    with self.assertRaises(ValueError):
                        PoseComparison(path)

    def test_inclusive_twenty_degree_boundary(self):
        comparison = PoseComparison(self.path)
        pose = next(iter(comparison.reference_angles))
        reference = comparison.reference_angles[pose]
        name = next(n for n, v in reference.items() if 20 < v < 160)
        for delta, expected in ((15, True), (-15, True), (20, True), (-20, True), (20.001, False), (-20.001, False)):
            measured = {**reference, name: reference[name] + delta}
            result = comparison.evaluate_angles(pose, measured)
            self.assertEqual(result['is_standard'], expected)
            self.assertEqual(result['angles'][name]['within_tolerance'], expected)

    def test_unseen_joint_cannot_pass(self):
        comparison = PoseComparison(self.path)
        pose = next(iter(comparison.reference_poses))
        result = comparison.compare(pose, comparison.reference_poses[pose], np.zeros(33))
        self.assertIsNone(result['is_standard'])
        self.assertEqual(len(result['unavailable_angles']), 8)
