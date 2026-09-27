"""API tests use real decoding, features, LightGBM and fixed JSON feedback."""
import csv
import base64
import importlib.util
from io import BytesIO
from pathlib import Path
import types
import unittest
from unittest.mock import patch

import numpy as np
from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image

from utils.feature_extractor import FeatureExtractor
from utils.pose_detector import PoseDetector, NoPoseDetected

ROOT = Path(__file__).resolve().parents[1]


class PhotoPredictionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location("photo_routes_under_test", ROOT / "app/routes.py")
        cls.routes = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.routes)
        app = FastAPI()
        app.include_router(cls.routes.router)
        cls.client = TestClient(app)
        with (ROOT / "utils/yoga_5poses_mediapipe_dataset_complete.csv").open(encoding="utf-8") as stream:
            cls.sample = next(csv.DictReader(stream))
        cls.points = np.array([[float(cls.sample[f"lm_{i}_{axis}"]) for axis in "xyz"] for i in range(33)])

    def test_feature_schema_and_coordinates(self):
        extractor = FeatureExtractor()
        self.assertEqual(78, self.routes.lightgbm_loader.model.n_features_in_)
        self.assertEqual(self.routes.lightgbm_loader.feature_names,
                         extractor.feature_names() + ["knee_angle_diff_deg"])
        features = extractor.extract_features(self.points)
        self.assertEqual(features.shape, (77,))
        np.testing.assert_array_equal(features[:69],
                                      self.points[list(extractor.KEYPOINT_INDICES)].ravel())

    def test_upload_runs_real_classifier(self):
        image = BytesIO()
        Image.new("RGB", (128, 128), "white").save(image, format="PNG")
        with patch.object(self.routes.pose_detector, "extract", return_value=(self.points, np.ones(33))):
            response = self.client.post("/api/predict", files={"file": ("pose.png", image.getvalue(), "image/png")})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertIn(response.json()["pose"], self.routes.lightgbm_loader.POSE_CLASSES_ZH)
        self.assertTrue(0 <= response.json()["confidence"] <= 1)
        self.assertTrue(response.json()["feedback"])
        self.assertEqual(response.json()["comparison"]["tolerance_deg"], 20)
        self.assertEqual(len(response.json()["comparison"]["angles"]), 8)
        self.assertNotIn("similarity", response.json()["comparison"])
        data = response.json()
        from utils.pose_rating import ENCOURAGEMENTS, build_rating
        expected_rating = build_rating(data["comparison"])
        actual_rating = dict(data["rating"])
        encouragement = actual_rating.pop("encouragement")
        expected_rating.pop("encouragement")
        self.assertEqual(actual_rating, expected_rating)
        self.assertIn(encouragement, ENCOURAGEMENTS[f'{actual_rating["score"]:g}'])
        self.assertEqual(base64.b64decode(data["original_image"].split(",")[1]), image.getvalue())
        self.assertEqual(len(data["landmarks"]), 33)
        with Image.open(BytesIO(base64.b64decode(data["skeleton_image"].split(",")[1]))) as skeleton:
            self.assertEqual(skeleton.format, "PNG")
            self.assertEqual(skeleton.size, (128, 128))

    def test_missing_file_and_old_json_rejected(self):
        for kwargs in ({}, {"json": {"landmarks": self.points.tolist()}}):
            self.assertEqual(self.client.post("/api/predict", **kwargs).status_code, 422)

    def test_classification_confidence_threshold(self):
        for confidence in (0.29, 0.3, 0.31):
            with self.subTest(confidence=confidence), patch.object(
                self.routes.lightgbm_loader, "predict", return_value=("樹式", "", confidence)
            ):
                result = self.routes._predict_landmarks(self.points, np.ones(33))
            self.assertEqual(result.pose, "尚無法辨識" if confidence <= 0.3 else "樹式")
            if confidence <= 0.3:
                self.assertEqual(result.pose_en, "")
                self.assertEqual(result.sub_pose, "")
                self.assertEqual(result.feedback, "尚無法辨識")
                self.assertEqual(result.suggestions, [])

    def test_unrated_result_has_no_classification_and_fixed_feedback(self):
        visibility = np.zeros(33)
        visibility[[11, 12, 23, 24]] = 1
        result = self.routes._predict_landmarks(self.points, visibility)
        self.assertIsNone(result.rating.score)
        for key in ("pose", "pose_en", "sub_pose", "sub_pose_en"):
            self.assertEqual(getattr(result, key), "")
        self.assertEqual(result.feedback, "調整姿勢再重新拍攝")
        self.assertEqual(result.suggestions, [])
        self.assertEqual(result.comparison["pose_name_zh"], "")

    def test_upload_with_json_feedback(self):
        from utils.json_feedback import JsonFeedback
        image = BytesIO()
        Image.new("RGB", (128, 128), "white").save(image, format="PNG")
        with patch.object(self.routes, "feedback_generator", JsonFeedback()), patch.object(
            self.routes.pose_detector, "extract", return_value=(self.points, np.ones(33))
        ):
            response = self.client.post("/api/predict", files={"file": ("pose.png", image.getvalue(), "image/png")})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertNotEqual(response.json()["feedback"], "測試回饋")
        self.assertTrue(response.json()["suggestions"])

    def test_invalid_or_empty_image(self):
        for content in (b"", b"not a photo"):
            response = self.client.post("/api/predict", files={"file": ("fake.jpg", content, "image/jpeg")})
            self.assertEqual(response.status_code, 400, response.text)

    def test_size_limit(self):
        with patch.object(self.routes, "MAX_IMAGE_BYTES", 4):
            response = self.client.post("/api/predict", files={"file": ("large.jpg", b"12345")})
        self.assertEqual(response.status_code, 413)

    def test_no_person(self):
        image = BytesIO()
        Image.new("RGB", (128, 128), "white").save(image, format="PNG")
        with patch("utils.pose_detector.mp.tasks.vision.PoseLandmarker.create_from_options") as factory:
            factory.return_value.__enter__.return_value.detect.return_value.pose_landmarks = []
            response = self.client.post("/api/predict", files={"file": ("blank.png", image.getvalue())})
        self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(response.json()["detail"], "調整姿勢再重新拍攝")

    def test_exif_orientation_and_visibility(self):
        photo = Image.new("RGB", (40, 20), "red")
        exif = photo.getexif()
        exif[274] = 6
        image = BytesIO()
        photo.save(image, format="JPEG", exif=exif)
        points = [types.SimpleNamespace(x=0.1, y=0.2, z=-0.3, visibility=0.7)] * 33
        with patch("utils.pose_detector.mp.tasks.vision.PoseLandmarker.create_from_options") as factory:
            detect = factory.return_value.__enter__.return_value.detect
            detect.return_value.pose_landmarks = [points]
            landmarks, visibility = PoseDetector().extract(image.getvalue())
            self.assertEqual(detect.call_args.args[0].numpy_view().shape, (40, 20, 3))
        self.assertEqual(landmarks.shape, (33, 3))
        np.testing.assert_allclose(visibility, 0.7)


if __name__ == "__main__":
    unittest.main()
