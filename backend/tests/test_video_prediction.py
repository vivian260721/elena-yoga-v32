"""Real MP4 decoding plus API regression tests without downloading an LLM."""
import csv
import importlib.util
from io import BytesIO
from pathlib import Path
import types
import unittest
from unittest.mock import patch

import av
import numpy as np
from fastapi import FastAPI
from fastapi.testclient import TestClient

from utils.video_analysis import analyze_video, VideoLimitExceeded

ROOT = Path(__file__).resolve().parents[1]


def make_video(count=20, fps=10):
    output = BytesIO()
    with av.open(output, mode="w", format="mp4") as container:
        stream = container.add_stream("mpeg4", rate=fps)
        stream.width = 64
        stream.height = 64
        stream.pix_fmt = "yuv420p"
        for _ in range(count):
            frame = av.VideoFrame.from_ndarray(np.full((64, 64, 3), 255, dtype=np.uint8), format="rgb24")
            for packet in stream.encode(frame):
                container.mux(packet)
        for packet in stream.encode():
            container.mux(packet)
    return output.getvalue()


class VideoPredictionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location("video_routes_under_test", ROOT / "app/routes.py")
        cls.routes = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.routes)
        app = FastAPI()
        app.include_router(cls.routes.router)
        cls.client = TestClient(app)
        cls.video = make_video()
        with (ROOT / "utils/yoga_5poses_mediapipe_dataset_complete.csv").open(encoding="utf-8") as stream:
            row = next(csv.DictReader(stream))
        cls.points = [types.SimpleNamespace(
            x=float(row[f"lm_{i}_x"]), y=float(row[f"lm_{i}_y"]),
            z=float(row[f"lm_{i}_z"]), visibility=1.0,
        ) for i in range(33)]

    def upload(self, content):
        return self.client.post("/api/predict-video", files={"file": ("clip.mp4", content, "video/mp4")})

    def test_real_decode_sampling_and_mixed_results(self):
        with patch("utils.video_analysis.mp.tasks.vision.PoseLandmarker.create_from_options") as factory:
            detect = factory.return_value.__enter__.return_value.detect_for_video
            detect.side_effect = [types.SimpleNamespace(pose_landmarks=points)
                                  for points in ([self.points], [], [self.points], [])]
            response = self.upload(self.video)
            self.assertEqual([call.args[1] for call in detect.call_args_list], [0, 500, 1000, 1500])
            factory.return_value.__exit__.assert_called_once()
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()
        self.assertEqual(data["sampled_frames"], 4)
        self.assertEqual(data["feedback_interval_seconds"], 2.0)
        self.assertEqual([frame["is_feedback_frame"] for frame in data["frames"]], [True, False, False, False])
        self.assertEqual(data["analyzed_frames"], 2)
        self.assertEqual(data["unavailable_frames"], 2)
        self.assertEqual(data["standard_frames"] + data["nonstandard_frames"] + data["indeterminate_frames"], 2)
        frame = data["frames"][0]["prediction"]
        from utils.pose_rating import ENCOURAGEMENTS, build_rating
        expected_rating = build_rating(frame["comparison"])
        actual_rating = dict(frame["rating"])
        encouragement = actual_rating.pop("encouragement")
        expected_rating.pop("encouragement")
        self.assertEqual(actual_rating, expected_rating)
        self.assertIn(encouragement, ENCOURAGEMENTS[f'{actual_rating["score"]:g}'])
        self.assertEqual(len(frame["landmarks"]), 33)
        self.assertEqual(frame["comparison"]["tolerance_deg"], 20)
        self.assertTrue(frame["skeleton_image"].startswith("data:image/jpeg;base64,"))
        self.assertIsNone(data["frames"][1]["prediction"])
        self.assertTrue(data["frames"][1]["original_image"].startswith("data:image/jpeg;base64,"))

    def test_real_full_inference_on_blank_video(self):
        response = self.upload(make_video(count=2))
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["analyzed_frames"], 0)
        self.assertEqual(response.json()["unavailable_frames"], 1)
        self.assertFalse(response.json()["frames"][0]["is_feedback_frame"])

    def test_feedback_is_at_least_two_seconds_apart(self):
        video = make_video(count=50)
        with patch("utils.video_analysis.mp.tasks.vision.PoseLandmarker.create_from_options") as factory:
            factory.return_value.__enter__.return_value.detect_for_video.return_value.pose_landmarks = [self.points]
            response = self.upload(video)
        self.assertEqual(response.status_code, 200, response.text)
        feedback_times = [
            frame["timestamp_seconds"] for frame in response.json()["frames"]
            if frame["is_feedback_frame"]
        ]
        self.assertEqual(feedback_times, [0.0, 2.0, 4.0])

    def test_invalid_empty_and_missing_video(self):
        self.assertEqual(self.client.post("/api/predict-video").status_code, 422)
        for content in (b"", b"not a video"):
            self.assertEqual(self.upload(content).status_code, 400)

    def test_size_and_duration_limits(self):
        with patch.object(self.routes, "MAX_VIDEO_BYTES", 4):
            self.assertEqual(self.upload(b"12345").status_code, 413)
        with patch("utils.video_analysis.MAX_VIDEO_SECONDS", 1):
            self.assertEqual(self.upload(self.video).status_code, 413)

    def test_resource_closed_when_prediction_fails(self):
        with patch("utils.video_analysis.mp.tasks.vision.PoseLandmarker.create_from_options") as factory:
            factory.return_value.__enter__.return_value.detect_for_video.return_value.pose_landmarks = [self.points]
            with patch.object(self.routes, "_predict_landmarks", side_effect=RuntimeError("test failure")):
                response = self.upload(self.video)
            factory.return_value.__exit__.assert_called_once()
        self.assertEqual(response.status_code, 500)

    def test_decode_budget(self):
        with patch("utils.video_analysis.MAX_DECODED_FRAMES", 1):
            with patch("utils.video_analysis.mp.tasks.vision.PoseLandmarker.create_from_options") as factory:
                factory.return_value.__enter__.return_value.detect_for_video.return_value.pose_landmarks = []
                with self.assertRaises(VideoLimitExceeded):
                    list(analyze_video(BytesIO(self.video)))

    def test_variable_timestamps_and_rotation(self):
        from PIL import Image
        photo = Image.new("RGB", (80, 40), "white")
        decoded = [types.SimpleNamespace(
            width=80, height=40, time=time, duration=0, time_base=None,
            rotation=90, to_image=lambda: photo.copy(),
        ) for time in (10.0, 10.2, 10.9, 11.7)]
        with patch("utils.video_analysis.av.open") as opened:
            container = opened.return_value.__enter__.return_value
            container.streams.video = [types.SimpleNamespace(
                duration=None, time_base=None, codec_context=types.SimpleNamespace(width=80, height=40),
            )]
            container.decode.return_value = iter(decoded)
            with patch("utils.video_analysis.mp.tasks.vision.PoseLandmarker.create_from_options") as factory:
                detect = factory.return_value.__enter__.return_value.detect_for_video
                detect.return_value.pose_landmarks = []
                samples = list(analyze_video(BytesIO(b"test")))
                self.assertEqual([call.args[1] for call in detect.call_args_list], [0, 900, 1700])
                self.assertEqual(detect.call_args.args[0].numpy_view().shape, (80, 40, 3))
        self.assertEqual(len(samples), 3)
        self.assertEqual(Image.open(BytesIO(samples[0][1])).size, (40, 80))

    def test_video_track_required(self):
        with patch("utils.video_analysis.av.open") as opened:
            opened.return_value.__enter__.return_value.streams.video = []
            self.assertEqual(self.upload(b"audio-only").status_code, 400)
