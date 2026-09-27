import unittest
from utils.pose_comparison import PoseComparison
from utils.pose_rating import ENCOURAGEMENTS, build_rating


class PoseRatingTests(unittest.TestCase):
    def rate(self, statuses, downdog=False):
        names = list(PoseComparison.ANGLE_JOINTS)
        if downdog:
            names = [f"{side}_{joint}_angle" for side in ("L", "R")
                     for joint in ("elbow", "shoulder", "hip", "knee")]
        return build_rating({
            "pose_name_zh": "\u4e0b\u72ac\u5f0f" if downdog else "\u6a39\u5f0f",
            "angles": {name: {"within_tolerance": status} for name, status in zip(names, statuses)},
        })

    def test_other_pose_table(self):
        for correct, expected in enumerate((0, 1, 2, 3, 3.5, 4, 4, 4.5, 5)):
            with self.subTest(correct=correct):
                result = self.rate([True] * correct + [False] * (8 - correct))
                self.assertEqual(result["score"], expected)
                self.assertEqual(result["hearts"], expected)
                self.assertEqual(result["total_count"], 8)
                self.assertEqual(result["correct_ratio"], correct / 8)
                self.assertIn(result["encouragement"], ENCOURAGEMENTS[str(expected)])

    def test_downdog_table(self):
        for correct, expected in enumerate((0, 1, 3, 4.5, 5)):
            with self.subTest(correct=correct):
                result = self.rate([True] * correct + [False] * (4 - correct) + [None] * 4, True)
                self.assertEqual(result["score"], expected)
                self.assertEqual(result["total_count"], 4)
                self.assertEqual(result["correct_count"], correct)
                self.assertEqual(result["correct_ratio"], correct / 4)

    def test_downdog_prefers_complete_side_before_correct_count(self):
        result = self.rate([True, True, True, None] + [True, False, False, False], True)
        self.assertEqual(result["score"], 1)
        self.assertEqual(result["detected_count"], 4)

    def test_downdog_prefers_more_correct_when_equally_complete(self):
        result = self.rate([True, False, False, False] + [True, True, True, False], True)
        self.assertEqual(result["score"], 4.5)
        self.assertEqual(result["correct_count"], 3)

    def test_missing_angles_do_not_inflate_score(self):
        result = self.rate([True] * 4 + [None] * 4)
        self.assertEqual(result["score"], 3.5)
        self.assertEqual(result["correct_ratio"], 0.5)
        self.assertEqual(result["detected_count"], 4)

    def test_no_detected_angles_is_unrated(self):
        for downdog in (False, True):
            result = self.rate([None] * 8, downdog)
            for key in ("score", "hearts", "encouragement", "correct_ratio"):
                self.assertIsNone(result[key])

    def test_api_preserves_fractional_and_zero_scores(self):
        from app.routes import RatingResponse
        for correct, expected in ((0, 0), (4, 3.5), (7, 4.5)):
            result = self.rate([True] * correct + [False] * (8 - correct))
            response = RatingResponse(**result).model_dump()
            self.assertEqual(response["score"], expected)
            self.assertEqual(response["hearts"], expected)
