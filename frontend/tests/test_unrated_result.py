import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from services.result_feedback import UNRATED_FEEDBACK, normalize_result
from services.video_timeline import frame_view


class UnratedResultTests(unittest.TestCase):
    def test_backend_decisions_are_preserved(self):
        for confidence in (0.29, 0.3, 0.31):
            result = normalize_result({"pose": "樹式", "confidence": confidence,
                                       "rating": {"score": 3}})
            self.assertEqual(result["pose"], "樹式")
        result = normalize_result({"pose": "樹式", "confidence": 0.1, "rating": None})
        self.assertEqual(result["pose"], "樹式")
        self.assertNotIn("feedback", result)

    def test_unrated_frame_does_not_reuse_previous_pose_or_feedback(self):
        frames = [
            {"timestamp_seconds": 0, "is_feedback_frame": True,
             "prediction": {"pose": "樹式", "rating": {"score": 5},
                            "feedback": "很好", "suggestions": ["保持"]}},
            {"timestamp_seconds": 0.5, "is_feedback_frame": False,
             "prediction": {"pose": "", "rating": {"score": None},
                            "feedback": UNRATED_FEEDBACK, "suggestions": []}},
        ]
        result, timestamp = frame_view(frames, 1)
        self.assertEqual(result["pose"], "")
        self.assertEqual(result["feedback"], UNRATED_FEEDBACK)
        self.assertEqual(result["suggestions"], [])
        self.assertEqual(timestamp, "")

    def test_zero_score_still_keeps_classification(self):
        result = {"pose": "樹式", "rating": {"score": 0}, "feedback": "原回饋"}
        self.assertEqual(normalize_result(result), result)

    def test_card_displays_backend_unrated_response(self):
        from nicegui import Client, ui
        from components.result_display_card import build
        client = Client(ui.page('/unrated-test'))
        try:
            with client:
                build(ui.column(), {"pose": "", "rating": {"score": None},
                                    "feedback": UNRATED_FEEDBACK, "suggestions": []})
            labels = [getattr(element, 'text', '') for element in client.elements.values()]
            self.assertIn(UNRATED_FEEDBACK, labels)
            self.assertNotIn("不應顯示的分類", labels)
            self.assertNotIn("舊回饋", labels)
            self.assertNotIn("• 舊建議", labels)
        finally:
            client.delete()
