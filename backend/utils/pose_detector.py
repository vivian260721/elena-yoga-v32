"""Decode photos and extract MediaPipe image landmarks (not world coordinates)."""
from io import BytesIO
from pathlib import Path
import warnings
import mediapipe as mp
import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

MAX_IMAGE_BYTES = 10 * 1024 * 1024
MAX_IMAGE_PIXELS = 20_000_000
DEFAULT_MODEL_PATH = Path(__file__).resolve().parents[1] / "Model/pose_landmarker_full.task"


class NoPoseDetected(ValueError):
    pass


class PoseDetector:
    def __init__(self, model_path=DEFAULT_MODEL_PATH):
        self.model_path = Path(model_path)

    def extract(self, content: bytes):
        if not content:
            raise ValueError("照片不可為空")
        if len(content) > MAX_IMAGE_BYTES:
            raise ValueError("照片不可超過 10 MiB")
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                with Image.open(BytesIO(content)) as photo:
                    if photo.format not in {"JPEG", "PNG", "WEBP"}:
                        raise ValueError("僅支援 JPEG、PNG 或 WebP 照片")
                    if photo.width * photo.height > MAX_IMAGE_PIXELS:
                        raise ValueError("照片不可超過 2000 萬像素")
                    rgb = np.array(ImageOps.exif_transpose(photo).convert("RGB"))
        except (UnidentifiedImageError, OSError, Image.DecompressionBombError,
                Image.DecompressionBombWarning) as exc:
            raise ValueError("無法讀取照片，請上傳完整的 JPEG、PNG 或 WebP 圖片") from exc
        if not self.model_path.is_file():
            raise RuntimeError("缺少 MediaPipe 模型，請執行 python scripts/download_pose_model.py")
        options = mp.tasks.vision.PoseLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(model_asset_path=str(self.model_path)),
            running_mode=mp.tasks.vision.RunningMode.IMAGE,
            num_poses=1,
            min_pose_detection_confidence=0.5,
            min_pose_presence_confidence=0.5,
        )
        # Per-request context closes native resources and avoids shared state.
        with mp.tasks.vision.PoseLandmarker.create_from_options(options) as detector:
            result = detector.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb))
        return self.parse_result(result)

    @staticmethod
    def parse_result(result):
        if not result.pose_landmarks:
            raise NoPoseDetected("照片中未偵測到人體，請上傳清楚的單人全身照片")
        points = result.pose_landmarks[0]
        landmarks = np.array([[p.x, p.y, p.z] for p in points], dtype=np.float32)
        visibility = np.array([p.visibility for p in points], dtype=np.float32)
        if (landmarks.shape != (33, 3) or not np.isfinite(landmarks).all()
                or visibility.shape != (33,) or not np.isfinite(visibility).all()):
            raise NoPoseDetected("無法取得完整人體關鍵點，請更換照片")
        return landmarks, visibility
