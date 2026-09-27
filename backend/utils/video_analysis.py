"""Bounded video decoding and timestamp-based sampling with one Full tracker."""
from io import BytesIO
import math

import av
import mediapipe as mp
import numpy as np

from utils.pose_detector import DEFAULT_MODEL_PATH, NoPoseDetected, PoseDetector

MAX_VIDEO_BYTES = 50 * 1024 * 1024
MAX_VIDEO_SECONDS = 60
SAMPLE_FPS = 2
FEEDBACK_INTERVAL_SECONDS = 2.0
MAX_SAMPLES = MAX_VIDEO_SECONDS * SAMPLE_FPS
MAX_DECODED_FRAMES = 7200
MAX_FRAME_PIXELS = 3840 * 2160
PREVIEW_MAX_SIDE = 640


class VideoLimitExceeded(ValueError):
    pass


def analyze_video(stream):
    """Yield timestamp, preview JPEG, landmarks/visibility, or an unavailable reason.

    Decode sequentially using presentation timestamps (including variable FPS).
    The caller owns the upload stream; native decoder/tracker resources close here.
    """
    if not DEFAULT_MODEL_PATH.is_file():
        raise RuntimeError("缺少 Full 模型，請執行 python scripts/download_pose_model.py")
    options = mp.tasks.vision.PoseLandmarkerOptions(
        base_options=mp.tasks.BaseOptions(model_asset_path=str(DEFAULT_MODEL_PATH)),
        running_mode=mp.tasks.vision.RunningMode.VIDEO,
        num_poses=1,
        min_pose_detection_confidence=0.5,
        min_pose_presence_confidence=0.5,
        min_tracking_confidence=0.5,
    )
    try:
        with av.open(stream, mode="r") as container:
            if not container.streams.video:
                raise ValueError("檔案沒有可讀取的影片軌道")
            video = container.streams.video[0]
            if video.duration is not None and video.time_base is not None:
                if float(video.duration * video.time_base) > MAX_VIDEO_SECONDS + 0.001:
                    raise VideoLimitExceeded("影片不可超過 60 秒，請先裁切")
            if video.codec_context.width * video.codec_context.height > MAX_FRAME_PIXELS:
                raise VideoLimitExceeded("影片解析度不可超過 3840×2160 像素總量")
            first_time = None
            previous_time = -1.0
            next_sample = 0.0
            samples = 0
            decoded = 0
            with mp.tasks.vision.PoseLandmarker.create_from_options(options) as detector:
                for frame in container.decode(video):
                    decoded += 1
                    if decoded > MAX_DECODED_FRAMES:
                        raise VideoLimitExceeded("影片影格數過多，請降低影格率或縮短影片")
                    if frame.width * frame.height > MAX_FRAME_PIXELS:
                        raise VideoLimitExceeded("影片解析度過高")
                    if frame.time is None or not math.isfinite(frame.time):
                        raise ValueError("影片缺少有效時間戳，請轉存為 MP4 後重試")
                    if first_time is None:
                        first_time = frame.time
                    timestamp = float(frame.time - first_time)
                    if timestamp < previous_time:
                        raise ValueError("影片時間戳順序異常，請轉存為 MP4 後重試")
                    previous_time = timestamp
                    duration = float(frame.duration * frame.time_base) if frame.duration and frame.time_base else 0
                    if timestamp >= MAX_VIDEO_SECONDS or timestamp + duration > MAX_VIDEO_SECONDS + 0.001:
                        raise VideoLimitExceeded("影片不可超過 60 秒，請先裁切")
                    if timestamp + 1e-9 < next_sample:
                        continue
                    if samples >= MAX_SAMPLES:
                        raise VideoLimitExceeded("影片取樣影格數過多")
                    next_sample = (math.floor(timestamp * SAMPLE_FPS + 1e-9) + 1) / SAMPLE_FPS
                    samples += 1
                    photo = frame.to_image()
                    # FFmpeg display-matrix rotation is counterclockwise in degrees.
                    rotation = frame.rotation
                    if rotation:
                        photo = photo.rotate(rotation, expand=True)
                    photo.thumbnail((PREVIEW_MAX_SIDE, PREVIEW_MAX_SIDE))
                    rgb = np.ascontiguousarray(photo.convert("RGB"))
                    detected = detector.detect_for_video(
                        mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb), round(timestamp * 1000),
                    )
                    output = BytesIO()
                    photo.save(output, format="JPEG", quality=85)
                    try:
                        landmarks, visibility = PoseDetector.parse_result(detected)
                        reason = None
                    except NoPoseDetected:
                        landmarks, visibility = None, None
                        reason = "此影格未偵測到可分析的人體"
                    yield timestamp, output.getvalue(), landmarks, visibility, reason
            if decoded == 0:
                raise ValueError("影片沒有可解碼的影格")
    except av.FFmpegError as exc:
        raise ValueError("無法解碼影片，請上傳完整的 MP4、MOV 或 WebM；必要時轉為 H.264 MP4") from exc
