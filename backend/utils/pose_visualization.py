"""Render angle assessment on the original, EXIF-oriented photo."""
import base64
import math
from io import BytesIO

from PIL import Image, ImageDraw, ImageOps

from utils.normalizer import Normalizer
from utils.pose_comparison import PoseComparison


CONNECTIONS = (
    (0, 1), (1, 2), (2, 3), (3, 7), (0, 4), (4, 5), (5, 6),
    (6, 8), (9, 10), (11, 12), (11, 13), (13, 15), (15, 17),
    (15, 19), (15, 21), (17, 19), (12, 14), (14, 16), (16, 18),
    (16, 20), (16, 22), (18, 20), (11, 23), (12, 24), (23, 24),
    (23, 25), (24, 26), (25, 27), (26, 28), (27, 29), (28, 30),
    (29, 31), (30, 32), (27, 31), (28, 32),
)
COLORS = {"correct": "#00ff00", "incorrect": "#ff0000", "unknown": "#808080"}


def target_direction(base, target, direction, upward=False):
    """Choose a target ray; image y decreases toward the top of the photo."""
    offset = math.radians(target)
    preferred = base + direction * offset
    if upward:
        return min((preferred, base - direction * offset), key=math.sin)
    return preferred


def target_angle_segments(landmarks, visibility, comparison, image_size=None):
    """Target polylines in normalized assessment coordinates.

    Keep the proximal segment fixed (torso for shoulders), and choose the
    target on the current bend's side. Combined shoulder/elbow and hip/knee
    corrections retain the original torso segment and both limb lengths,
    applying both target angles along a connected four-point chain.
    With image_size, preserve the moving limb's pixel length while retaining
    the normalized target angle used by the reference CSV and red/green lights.
    """
    segments = {}
    goddess = comparison.get("pose_name_zh") == "女神式"
    sx, sy = (max(1, image_size[0] - 1), max(1, image_size[1] - 1)) if image_size else (1, 1)
    for name, (a, b, c) in PoseComparison.ANGLE_JOINTS.items():
        assessment = comparison["angles"].get(name, {})
        target = assessment.get("reference_deg")
        if assessment.get("within_tolerance") is not False or target is None:
            continue
        if not math.isfinite(target) or not 0 <= target <= 180:
            continue
        if "shoulder" in name:
            a, c = c, a
        coords = [tuple(float(v) for v in landmarks[i][:2]) for i in (a, b, c)]
        if any(not math.isfinite(v) or not 0 <= v <= 1 for p in coords for v in p):
            continue
        if any(not math.isfinite(float(visibility[i])) or visibility[i] < Normalizer.CONFIDENCE_THRESHOLD
               for i in (a, b, c)):
            continue
        anchor, joint, moving = coords
        ux, uy = anchor[0] - joint[0], anchor[1] - joint[1]
        vx, vy = moving[0] - joint[0], moving[1] - joint[1]
        fixed_length, moving_length = math.hypot(ux, uy), math.hypot(vx, vy)
        if min(fixed_length, moving_length) <= 1e-12:
            continue
        direction = 1 if ux * vy - uy * vx >= 0 else -1
        theta = target_direction(math.atan2(uy, ux), target, direction,
                                 upward=goddess and "elbow" in name)
        pixel_length = math.hypot(vx * sx, vy * sy)
        moving_length = pixel_length / math.hypot(math.cos(theta) * sx, math.sin(theta) * sy)
        endpoint = (joint[0] + moving_length * math.cos(theta),
                    joint[1] + moving_length * math.sin(theta))
        segments[name] = (anchor, joint, endpoint)
    for side in ("L", "R"):
        for proximal, distal in (("shoulder", "elbow"), ("hip", "knee")):
            proximal_name, distal_name = f"{side}_{proximal}_angle", f"{side}_{distal}_angle"
            if proximal_name not in segments or distal_name not in segments:
                continue
            anchor, joint, new_bend = segments[proximal_name]
            old_joint, old_bend, old_end = (
                tuple(float(v) for v in landmarks[i][:2])
                for i in PoseComparison.ANGLE_JOINTS[distal_name]
            )
            ux, uy = old_joint[0] - old_bend[0], old_joint[1] - old_bend[1]
            vx, vy = old_end[0] - old_bend[0], old_end[1] - old_bend[1]
            direction = 1 if ux * vy - uy * vx >= 0 else -1
            theta = target_direction(
                math.atan2(joint[1] - new_bend[1], joint[0] - new_bend[0]),
                comparison["angles"][distal_name]["reference_deg"], direction,
                upward=goddess and distal == "elbow",
            )
            length = math.hypot(vx * sx, vy * sy) / math.hypot(math.cos(theta) * sx, math.sin(theta) * sy)
            new_end = (new_bend[0] + length * math.cos(theta),
                       new_bend[1] + length * math.sin(theta))
            segments[proximal_name] = (anchor, joint, new_bend, new_end)
            del segments[distal_name]
    return list(segments.values())



def _user_center_and_scale(landmarks, visibility):
    """Return the same center/scale used by Normalizer, but in image coordinates."""
    import numpy as np
    points = np.asarray(landmarks, dtype=float)
    vis = np.asarray(visibility, dtype=float)
    reliable = vis >= Normalizer.CONFIDENCE_THRESHOLD
    if not reliable.any():
        return None, None
    xy = points[:, :2]
    hips_ok = reliable[Normalizer.LEFT_HIP] and reliable[Normalizer.RIGHT_HIP]
    shoulders_ok = reliable[Normalizer.LEFT_SHOULDER] and reliable[Normalizer.RIGHT_SHOULDER]
    if hips_ok:
        center = (xy[Normalizer.LEFT_HIP] + xy[Normalizer.RIGHT_HIP]) / 2.0
    elif shoulders_ok:
        center = (xy[Normalizer.LEFT_SHOULDER] + xy[Normalizer.RIGHT_SHOULDER]) / 2.0
    else:
        center = xy[reliable].mean(axis=0)
    body_radius = np.linalg.norm(xy[reliable] - center, axis=1).max()
    if hips_ok and shoulders_ok:
        shoulder_center = (xy[Normalizer.LEFT_SHOULDER] + xy[Normalizer.RIGHT_SHOULDER]) / 2.0
        hip_center = (xy[Normalizer.LEFT_HIP] + xy[Normalizer.RIGHT_HIP]) / 2.0
        torso_size = np.linalg.norm(shoulder_center - hip_center)
        scale = max(body_radius, Normalizer.TORSO_MULTIPLIER * torso_size)
    else:
        scale = body_radius
    if not math.isfinite(float(scale)) or scale <= 1e-12:
        return None, None
    return center, float(scale)


def user_proportioned_reference_landmarks(reference_normalized, landmarks, visibility, image_size, mirrored=False):
    """Build the blue target skeleton with reference directions + user's limb lengths.

    V3.2 keeps the *pose geometry/directions* from the reference CSV, but sizes each
    major body segment from the current user's MediaPipe landmarks in pixel space.
    This avoids V3.1's "another person's proportions" effect while also avoiding
    V2's angle-only ray reconstruction.
    """
    import numpy as np

    ref = np.asarray(reference_normalized, dtype=float).copy()
    user = np.asarray(landmarks, dtype=float)
    vis = np.asarray(visibility, dtype=float)
    if ref.shape != (33, 3) or user.shape != (33, 3) or vis.shape != (33,):
        return None
    if not np.isfinite(ref).all() or not np.isfinite(user).all() or not np.isfinite(vis).all():
        return None
    if mirrored:
        ref[:, 0] *= -1.0

    width, height = image_size
    px_scale = np.array([max(1, width - 1), max(1, height - 1)], dtype=float)
    center, scale = _user_center_and_scale(user, vis)
    if center is None:
        return None

    # Start with the V3.1 whole-body alignment as a safe fallback for face and
    # any degenerate/hidden segment. Major body joints are replaced below.
    out = ref.copy()
    out[:, :2] = ref[:, :2] * scale + center

    def pixel_length(a, b):
        d = (user[b, :2] - user[a, :2]) * px_scale
        length = float(np.linalg.norm(d))
        return length if math.isfinite(length) and length > 1e-6 else None

    def ref_direction(a_xy, b_xy):
        d = np.asarray(b_xy, dtype=float) - np.asarray(a_xy, dtype=float)
        denom = float(np.linalg.norm(d * px_scale))
        if not math.isfinite(denom) or denom <= 1e-12:
            return None
        return d / denom  # multiplying by a pixel length yields normalized dx/dy

    def place_from(start_xy, ref_start_xy, ref_end_xy, length_px):
        direction = ref_direction(ref_start_xy, ref_end_xy)
        if direction is None or length_px is None:
            return None
        return np.asarray(start_xy, dtype=float) + direction * length_px

    # Stable torso frame: center at the user's mid-hip, but use the reference
    # directions. Shoulder/hip widths and torso height come from the user.
    lh, rh, ls, rs = 23, 24, 11, 12
    user_midhip = (user[lh, :2] + user[rh, :2]) / 2.0
    user_midshoulder = (user[ls, :2] + user[rs, :2]) / 2.0
    ref_midhip = (ref[lh, :2] + ref[rh, :2]) / 2.0
    ref_midshoulder = (ref[ls, :2] + ref[rs, :2]) / 2.0

    hip_width = float(np.linalg.norm((user[rh, :2] - user[lh, :2]) * px_scale))
    shoulder_width = float(np.linalg.norm((user[rs, :2] - user[ls, :2]) * px_scale))
    torso_length = float(np.linalg.norm((user_midshoulder - user_midhip) * px_scale))

    hip_dir = ref_direction(ref[lh, :2], ref[rh, :2])
    shoulder_dir = ref_direction(ref[ls, :2], ref[rs, :2])
    torso_dir = ref_direction(ref_midhip, ref_midshoulder)
    if hip_dir is None or shoulder_dir is None or torso_dir is None:
        return out

    out[lh, :2] = user_midhip - hip_dir * hip_width / 2.0
    out[rh, :2] = user_midhip + hip_dir * hip_width / 2.0
    target_midshoulder = user_midhip + torso_dir * torso_length
    out[ls, :2] = target_midshoulder - shoulder_dir * shoulder_width / 2.0
    out[rs, :2] = target_midshoulder + shoulder_dir * shoulder_width / 2.0

    # Major limb chains. Every edge keeps the user's current pixel length while
    # taking its direction from the reference pose.
    chains = (
        (11, 13, 15), (12, 14, 16),
        (23, 25, 27), (24, 26, 28),
    )
    for chain in chains:
        for a, b in zip(chain, chain[1:]):
            placed = place_from(out[a, :2], ref[a, :2], ref[b, :2], pixel_length(a, b))
            if placed is not None:
                out[b, :2] = placed

    # Hands and feet branch from wrist/ankle. These preserve the user's local
    # segment lengths too, while following the reference direction.
    branches = (
        (15, 17), (15, 19), (15, 21),
        (16, 18), (16, 20), (16, 22),
        (27, 29), (27, 31),
        (28, 30), (28, 32),
    )
    for a, b in branches:
        placed = place_from(out[a, :2], ref[a, :2], ref[b, :2], pixel_length(a, b))
        if placed is not None:
            out[b, :2] = placed

    return out


def aligned_reference_landmarks(reference_normalized, landmarks, visibility, mirrored=False):
    """V3.1 compatibility helper: whole-body center/scale alignment."""
    import numpy as np
    ref = np.asarray(reference_normalized, dtype=float).copy()
    if ref.shape != (33, 3) or not np.isfinite(ref).all():
        return None
    if mirrored:
        ref[:, 0] *= -1.0
    center, scale = _user_center_and_scale(landmarks, visibility)
    if center is None:
        return None
    aligned = ref.copy()
    aligned[:, :2] = ref[:, :2] * scale + center
    return aligned

def data_url(content, mime):
    return f"data:{mime};base64,{base64.b64encode(content).decode('ascii')}"


def render_prediction(content, landmarks, visibility, comparison, reference_landmarks=None, output_format="PNG"):
    with Image.open(BytesIO(content)) as source:
        mime = Image.MIME[source.format]
        photo = ImageOps.exif_transpose(source).convert("RGB")
    width, height = photo.size
    radius = max(3, round(min(width, height) / 150))
    draw = ImageDraw.Draw(photo)
    points = []
    for index, (x, y, z) in enumerate(landmarks):
        angle_names = [name for name, indices in PoseComparison.ANGLE_JOINTS.items() if index in indices]
        checks = [comparison["angles"][name]["within_tolerance"] for name in angle_names]
        visible = bool(visibility[index] >= Normalizer.CONFIDENCE_THRESHOLD and 0 <= x <= 1 and 0 <= y <= 1)
        status = "unknown"
        if visible and checks:
            if any(check is False for check in checks):
                status = "incorrect"
            elif all(check is True for check in checks):
                status = "correct"
        points.append({
            "index": index, "x": float(x), "y": float(y), "z": float(z),
            "visibility": float(visibility[index]), "status": status,
            "color": COLORS[status], "angle_names": angle_names,
        })
    pixels = [(round(float(x) * (width - 1)), round(float(y) * (height - 1))) for x, y, _ in landmarks]
    for a, b in CONNECTIONS:
        if all(0 <= points[i]["x"] <= 1 and 0 <= points[i]["y"] <= 1 for i in (a, b)):
            draw.line([pixels[a], pixels[b]], fill="#ffffff", width=max(1, radius // 2))
    # V3.2: reference pose directions + the current user's body-segment lengths.
    # No reference_deg ray reconstruction is used for the blue guide.
    if reference_landmarks is not None and comparison.get("is_standard") is not True:
        aligned = user_proportioned_reference_landmarks(
            reference_landmarks, landmarks, visibility, (width, height),
            mirrored=bool(comparison.get("reference_mirrored", False)),
        )
        if aligned is not None:
            ref_pixels = [(round(float(x) * (width - 1)), round(float(y) * (height - 1)))
                          for x, y, _ in aligned]
            for a, b in CONNECTIONS:
                ax, ay = aligned[a, :2]
                bx, by = aligned[b, :2]
                # Draw only segments whose endpoints are near the image. This prevents
                # pathological off-canvas strokes while preserving the reference pose.
                if all(math.isfinite(v) for v in (ax, ay, bx, by)) and \
                   all(-0.15 <= v <= 1.15 for v in (ax, ay, bx, by)):
                    draw.line([ref_pixels[a], ref_pixels[b]], fill="#00e5ff",
                              width=max(4, radius * 2), joint="curve")
    for point, (x, y) in zip(points, pixels):
        if 0 <= point["x"] <= 1 and 0 <= point["y"] <= 1:
            draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=point["color"])
    output = BytesIO()
    photo.save(output, format=output_format)
    return {
        "original_image": data_url(content, mime),
        "skeleton_image": data_url(output.getvalue(), Image.MIME[output_format]),
        "image_width": width, "image_height": height, "landmarks": points,
    }
