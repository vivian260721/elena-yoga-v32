"""Exercise the actual joblib artifact and class/probability contract."""
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from models.lightgbm_loader import LightGBMLoader


class LightGBMLoaderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.loader = LightGBMLoader()

    def test_actual_joblib_prediction(self):
        self.assertEqual(self.loader.model_path.suffix, '.joblib')
        self.assertEqual(self.loader.class_labels, ['downdog', 'goddess', 'plank', 'tree', 'warrior2'])
        pose, subpose, confidence = self.loader.predict(np.zeros(77))
        self.assertIn(pose, ['下犬式', '女神式', '平板式', '樹式', '戰士二式'])
        self.assertEqual(pose, subpose)
        self.assertTrue(0 <= confidence <= 1)

    def test_probability_columns_follow_model_classes(self):
        for index, expected in enumerate(['下犬式', '女神式', '平板式', '樹式', '戰士二式']):
            probabilities = np.full((1, 5), 0.05)
            probabilities[0, index] = 0.8
            with patch.object(self.loader.model, 'predict_proba', return_value=probabilities):
                pose, _, confidence = self.loader.predict(np.zeros(77))
            self.assertEqual(pose, expected)
            self.assertAlmostEqual(confidence, 0.8)

    def test_invalid_input_and_probabilities(self):
        for features in [np.zeros(75), np.zeros((2, 77)), np.full(77, np.nan)]:
            with self.assertRaisesRegex(RuntimeError, 'finite feature vector'):
                self.loader.predict(features)
        with patch.object(self.loader.model, 'predict_proba', return_value=np.zeros((1, 5))):
            with self.assertRaisesRegex(RuntimeError, 'invalid class probabilities'):
                self.loader.predict(np.zeros(77))

    def test_missing_file(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(FileNotFoundError):
                LightGBMLoader(directory + '/missing.joblib')


    def test_knee_difference_reaches_model_in_training_order(self):
        self.assertEqual(self.loader.model_path.name, "anglediff_lightgbm.joblib")
        for left, right in ((150, 40), (40, 150), (90, 90)):
            features = np.arange(77, dtype=float)
            features[-2:] = left, right
            with patch.object(self.loader.model, 'predict_proba', return_value=np.full((1, 5), 0.2)) as predict:
                self.loader.predict(features)
            frame = predict.call_args.args[0]
            self.assertEqual(frame.shape, (1, 78))
            np.testing.assert_array_equal(frame.to_numpy()[0, :77], features)
            self.assertEqual(frame.iloc[0, -1], abs(left - right))
            self.assertEqual(list(frame.columns), self.loader.model.feature_name_)
