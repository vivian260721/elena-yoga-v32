"""Classification angles must retain depth, unlike projected XY angles."""
import unittest

import numpy as np

from utils.feature_extractor import FeatureExtractor


class FeatureExtractorTests(unittest.TestCase):
    def test_all_eight_joint_features_use_depth(self):
        joints = ((11, 13, 15), (12, 14, 16), (13, 11, 23), (14, 12, 24),
                  (11, 23, 25), (12, 24, 26), (23, 25, 27), (24, 26, 28))
        extractor = FeatureExtractor()
        for index, (a, b, c) in enumerate(joints):
            with self.subTest(feature=extractor.ANGLE_NAMES[index]):
                points = np.zeros((33, 3))
                # XY projection is 180 degrees; the XYZ vectors are orthogonal.
                points[a] = (1, 0, 1)
                points[c] = (-1, 0, 1)
                features = extractor.extract_features(points)
                self.assertAlmostEqual(features[69 + index], 90)
                transformed = extractor.extract_features(points * 3 + (4, 5, 6))
                self.assertAlmostEqual(transformed[69 + index], 90)

    def test_degenerate_joint_stays_finite(self):
        features = FeatureExtractor().extract_features(np.zeros((33, 3)))
        np.testing.assert_array_equal(features[-8:], np.zeros(8))
