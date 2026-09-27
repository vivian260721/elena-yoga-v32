import base64
from io import BytesIO
import unittest

import numpy as np
from PIL import Image

from utils.pose_comparison import PoseComparison
from utils.pose_visualization import render_prediction, target_angle_segments


class PoseVisualizationTests(unittest.TestCase):
    def correction_fixture(self, actual=37, target=137):
        points = np.full((33, 3), 0.5)
        points[11, :2] = (0.7, 0.5)
        points[15, :2] = (0.5 + 0.2 * np.cos(np.radians(actual)),
                           0.5 + 0.2 * np.sin(np.radians(actual)))
        angles = {name: {"within_tolerance": True} for name in PoseComparison.ANGLE_JOINTS}
        angles["L_elbow_angle"] = {"within_tolerance": False, "reference_deg": target}
        return points, np.ones(33), {"angles": angles}

    def test_target_137_degrees_preserves_length_and_mirrors(self):
        points, visibility, comparison = self.correction_fixture()
        for mirrored in (False, True):
            with self.subTest(mirrored=mirrored):
                current = points.copy()
                if mirrored:
                    current[:, 0] = 1 - current[:, 0]
                [(fixed, start, end)] = target_angle_segments(current, visibility, comparison)
                np.testing.assert_allclose(fixed, current[11, :2])
                ray = np.array(end) - start
                anchor = current[11, :2] - start
                angle = np.degrees(np.arccos(np.dot(ray, anchor) / np.linalg.norm(ray) / np.linalg.norm(anchor)))
                self.assertAlmostEqual(angle, 137)
                self.assertAlmostEqual(np.linalg.norm(ray), 0.2)
                self.assertGreater(end[1], start[1])

    def test_neon_blue_removed_at_tolerance_and_joint_turns_green(self):
        points, visibility, comparison = self.correction_fixture()
        stream = BytesIO()
        Image.new("RGB", (600, 300), "black").save(stream, "PNG")
        def render():
            result = render_prediction(stream.getvalue(), points, visibility, comparison)
            picture = Image.open(BytesIO(base64.b64decode(result["skeleton_image"].split(",")[1])))
            return result, np.asarray(picture)
        result, pixels = render()
        self.assertTrue(np.any(np.all(pixels == (0, 229, 255), axis=2)))
        self.assertEqual(result["landmarks"][13]["status"], "incorrect")
        evaluator = PoseComparison()
        measured = dict(evaluator.reference_angles["樹式"])
        measured["L_elbow_angle"] -= evaluator.ANGLE_TOLERANCE_DEG
        comparison["angles"] = evaluator.evaluate_angles("樹式", measured)["angles"]
        result, pixels = render()
        self.assertFalse(np.any(np.all(pixels == (0, 229, 255), axis=2)))
        self.assertEqual(result["landmarks"][13]["status"], "correct")

    def test_all_eight_guides_preserve_pixel_lengths_and_reference_angles(self):
        for name, (a, b, c) in PoseComparison.ANGLE_JOINTS.items():
            if "shoulder" in name:
                a, c = c, a
            for size in ((600, 300), (300, 600), (400, 400)):
                for mirrored in (False, True):
                    with self.subTest(name=name, size=size, mirrored=mirrored):
                        points = np.full((33, 3), 0.5)
                        points[a, :2] = (0.65, 0.4)
                        points[c, :2] = (0.6, 0.7)
                        if mirrored:
                            points[:, 0] = 1 - points[:, 0]
                        angles = {key: {"within_tolerance": True} for key in PoseComparison.ANGLE_JOINTS}
                        angles[name] = {"within_tolerance": False, "reference_deg": 137}
                        [(fixed, joint, end)] = target_angle_segments(points, np.ones(33), {"angles": angles}, size)
                        np.testing.assert_allclose(fixed, points[a, :2])
                        np.testing.assert_allclose(joint, points[b, :2])
                        scale = np.array(size) - 1
                        self.assertAlmostEqual(np.linalg.norm((np.array(end) - joint) * scale),
                                               np.linalg.norm((points[c, :2] - joint) * scale))
                        corrected = points.copy()
                        corrected[c, :2] = end
                        self.assertAlmostEqual(PoseComparison.measure_angles(corrected)[name], 137)

    def test_both_guide_arms_are_solid_and_lights_remain_visible(self):
        points, visibility, comparison = self.correction_fixture(target=90)
        for index in range(33):
            if index not in (11, 13, 15):
                points[index, :2] = (0.1, 0.1)
        stream = BytesIO()
        Image.new("RGB", (401, 401), "black").save(stream, "PNG")
        result = render_prediction(stream.getvalue(), points, visibility, comparison)
        picture = Image.open(BytesIO(base64.b64decode(result["skeleton_image"].split(",")[1])))
        # Both arms are continuous and thicker than the white skeleton.
        for offset in range(8, 73):
            self.assertEqual(picture.getpixel((200 + offset, 202)), (0, 229, 255))
            self.assertEqual(picture.getpixel((202, 200 + offset)), (0, 229, 255))
        self.assertEqual(picture.getpixel((200, 200)), (255, 0, 0))
        self.assertEqual(picture.getpixel((280, 200)), (255, 0, 0))

    def test_no_guide_for_unknown_hidden_or_degenerate_joint(self):
        for condition in ("unknown", "hidden", "degenerate", "offscreen"):
            points, visibility, comparison = self.correction_fixture()
            if condition == "unknown":
                comparison["angles"]["L_elbow_angle"]["within_tolerance"] = None
            elif condition == "hidden":
                visibility[15] = 0
            elif condition == "degenerate":
                points[15] = points[13]
            else:
                points[15, 0] = 1.1
            with self.subTest(condition=condition):
                self.assertEqual(target_angle_segments(points, visibility, comparison), [])

    def test_shoulder_keeps_torso_fixed(self):
        points, visibility, comparison = self.correction_fixture()
        comparison["angles"]["L_elbow_angle"]["within_tolerance"] = True
        comparison["angles"]["L_shoulder_angle"] = {"within_tolerance": False, "reference_deg": 90}
        points[11, :2], points[23, :2], points[13, :2] = (0.5, 0.5), (0.5, 0.8), (0.6, 0.6)
        [(fixed, start, end)] = target_angle_segments(points, visibility, comparison)
        np.testing.assert_allclose(fixed, points[23, :2])
        self.assertAlmostEqual(end[1], start[1])
        self.assertGreater(end[0], start[0])

    def test_combined_shoulder_elbow_preserves_torso_and_each_limb_length(self):
        for side in ("L", "R"):
            for size in ((600, 300), (300, 600)):
                for mirrored in (False, True):
                    with self.subTest(side=side, size=size, mirrored=mirrored):
                        shoulder_name = f"{side}_shoulder_angle"
                        elbow_name = f"{side}_elbow_angle"
                        elbow, shoulder, hip = PoseComparison.ANGLE_JOINTS[shoulder_name]
                        wrist = PoseComparison.ANGLE_JOINTS[elbow_name][2]
                        points = np.full((33, 3), 0.1)
                        points[shoulder, :2] = (0.5, 0.4)
                        points[hip, :2] = (0.5, 0.7)
                        points[elbow, :2] = (0.6, 0.5)
                        points[wrist, :2] = (0.8, 0.45)
                        if mirrored:
                            points[:, 0] = 1 - points[:, 0]
                        angles = {name: {"within_tolerance": True} for name in PoseComparison.ANGLE_JOINTS}
                        angles[shoulder_name] = {"within_tolerance": False, "reference_deg": 100}
                        angles[elbow_name] = {"within_tolerance": False, "reference_deg": 170}
                        [(fixed, joint, new_elbow, end)] = target_angle_segments(points, np.ones(33), {"angles": angles}, size)
                        np.testing.assert_allclose(fixed, points[hip, :2])
                        np.testing.assert_allclose(joint, points[shoulder, :2])
                        scale = np.array(size) - 1
                        corrected = points.copy()
                        corrected[elbow, :2], corrected[wrist, :2] = new_elbow, end
                        self.assertAlmostEqual(PoseComparison.measure_angles(corrected)[shoulder_name], 100)
                        self.assertAlmostEqual(PoseComparison.measure_angles(corrected)[elbow_name], 170)
                        for a, b in ((hip, shoulder), (shoulder, elbow), (elbow, wrist)):
                            self.assertAlmostEqual(np.linalg.norm((corrected[a, :2] - corrected[b, :2]) * scale),
                                                   np.linalg.norm((points[a, :2] - points[b, :2]) * scale))
                        # Once the shoulder passes, only the elbow guide remains.
                        angles[shoulder_name]["within_tolerance"] = True
                        [(fixed, joint, end)] = target_angle_segments(points, np.ones(33), {"angles": angles}, size)
                        np.testing.assert_allclose(joint, points[elbow, :2])

    def test_colors_unknown_and_original_bytes(self):
        stream = BytesIO()
        Image.new("RGB", (400, 400), "black").save(stream, "PNG")
        points = np.array([[(i % 6 + 1) / 8, (i // 6 + 1) / 8, 0] for i in range(33)])
        visibility = np.ones(33)
        angles = {name: {"within_tolerance": True} for name in PoseComparison.ANGLE_JOINTS}
        angles["L_elbow_angle"]["within_tolerance"] = False
        angles["R_knee_angle"]["within_tolerance"] = None
        visibility[23] = 0
        result = render_prediction(stream.getvalue(), points, visibility, {"angles": angles})
        self.assertEqual(base64.b64decode(result["original_image"].split(",")[1]), stream.getvalue())
        rendered = Image.open(BytesIO(base64.b64decode(result["skeleton_image"].split(",")[1])))
        for index, status, rgb in [(13, "incorrect", (255, 0, 0)), (14, "correct", (0, 255, 0)),
                                   (0, "unknown", (128, 128, 128)), (23, "unknown", (128, 128, 128)),
                                   (28, "unknown", (128, 128, 128))]:
            self.assertEqual(result["landmarks"][index]["status"], status)
            x, y, _ = points[index]
            self.assertEqual(rendered.getpixel((round(x * 399), round(y * 399))), rgb)

    def test_combined_hip_knee_chain_preserves_both_angles_and_limb_lengths(self):
        for side in ("L", "R"):
            for size in ((600, 300), (300, 600)):
                for mirrored in (False, True):
                    with self.subTest(side=side, size=size, mirrored=mirrored):
                        hip_name, knee_name = f"{side}_hip_angle", f"{side}_knee_angle"
                        shoulder, hip, knee = PoseComparison.ANGLE_JOINTS[hip_name]
                        ankle = PoseComparison.ANGLE_JOINTS[knee_name][2]
                        points = np.full((33, 3), 0.1)
                        points[shoulder, :2] = (0.5, 0.2)
                        points[hip, :2] = (0.5, 0.4)
                        points[knee, :2] = (0.65, 0.6)
                        points[ankle, :2] = (0.55, 0.8)
                        if mirrored:
                            points[:, 0] = 1 - points[:, 0]
                        angles = {name: {"within_tolerance": True} for name in PoseComparison.ANGLE_JOINTS}
                        angles[hip_name] = {"within_tolerance": False, "reference_deg": 120}
                        angles[knee_name] = {"within_tolerance": False, "reference_deg": 150}
                        [(fixed, start, new_knee, new_ankle)] = target_angle_segments(points, np.ones(33), {"angles": angles}, size)
                        np.testing.assert_allclose(fixed, points[shoulder, :2])
                        np.testing.assert_allclose(start, points[hip, :2])
                        corrected = points.copy()
                        corrected[knee, :2], corrected[ankle, :2] = new_knee, new_ankle
                        measured = PoseComparison.measure_angles(corrected)
                        self.assertAlmostEqual(measured[hip_name], 120)
                        self.assertAlmostEqual(measured[knee_name], 150)
                        scale = np.array(size) - 1
                        for a, b in ((shoulder, hip), (hip, knee), (knee, ankle)):
                            self.assertAlmostEqual(np.linalg.norm((corrected[a, :2] - corrected[b, :2]) * scale),
                                                   np.linalg.norm((points[a, :2] - points[b, :2]) * scale))
                        visibility = np.ones(33)
                        visibility[ankle] = 0
                        [(fixed, joint, end)] = target_angle_segments(points, visibility, {"angles": angles}, size)
                        np.testing.assert_allclose(fixed, points[shoulder, :2])
                        np.testing.assert_allclose(joint, points[hip, :2])

    def test_exif_orientation(self):
        photo = Image.new("RGB", (40, 20))
        exif = photo.getexif()
        exif[274] = 6
        stream = BytesIO()
        photo.save(stream, "JPEG", exif=exif)
        angles = {name: {"within_tolerance": True} for name in PoseComparison.ANGLE_JOINTS}
        result = render_prediction(stream.getvalue(), np.full((33, 3), 0.5), np.ones(33), {"angles": angles})
        self.assertEqual((result["image_width"], result["image_height"]), (20, 40))
        self.assertTrue(result["original_image"].startswith("data:image/jpeg;base64,"))

    def test_goddess_elbows_bend_up_for_single_and_combined_guides(self):
        for side in ("L", "R"):
            for mirrored in (False, True):
                for combined in (False, True):
                    for size in ((600, 300), (300, 600)):
                        with self.subTest(side=side, mirrored=mirrored, combined=combined, size=size):
                            shoulder_name, elbow_name = f"{side}_shoulder_angle", f"{side}_elbow_angle"
                            elbow, shoulder, hip = PoseComparison.ANGLE_JOINTS[shoulder_name]
                            wrist = PoseComparison.ANGLE_JOINTS[elbow_name][2]
                            points = np.full((33, 3), 0.1)
                            points[hip, :2], points[shoulder, :2] = (0.5, 0.8), (0.5, 0.4)
                            # Actual forearm points down: the goddess guide must reverse it.
                            points[elbow, :2], points[wrist, :2] = (0.7, 0.4), (0.75, 0.65)
                            if mirrored:
                                points[:, 0] = 1 - points[:, 0]
                            angles = {name: {"within_tolerance": True} for name in PoseComparison.ANGLE_JOINTS}
                            angles[elbow_name] = {"within_tolerance": False, "reference_deg": 85}
                            if combined:
                                angles[shoulder_name] = {"within_tolerance": False, "reference_deg": 100}
                            comparison = {"angles": angles, "pose_name_zh": "女神式"}
                            [guide] = target_angle_segments(points, np.ones(33), comparison, size)
                            new_elbow, new_wrist = guide[-2:]
                            self.assertLess(new_wrist[1], new_elbow[1])
                            corrected = points.copy()
                            corrected[elbow, :2], corrected[wrist, :2] = new_elbow, new_wrist
                            measured = PoseComparison.measure_angles(corrected)
                            self.assertAlmostEqual(measured[elbow_name], 85)
                            if combined:
                                self.assertAlmostEqual(measured[shoulder_name], 100)
                                np.testing.assert_allclose(guide[:2], points[[hip, shoulder], :2])
                            scale = np.array(size) - 1
                            for a, b in ((shoulder, elbow), (elbow, wrist)):
                                self.assertAlmostEqual(np.linalg.norm((corrected[a, :2] - corrected[b, :2]) * scale),
                                                       np.linalg.norm((points[a, :2] - points[b, :2]) * scale))
                            comparison["pose_name_zh"] = "戰士二式"
                            [other_guide] = target_angle_segments(points, np.ones(33), comparison, size)
                            self.assertGreater(other_guide[-1][1], other_guide[-2][1])
