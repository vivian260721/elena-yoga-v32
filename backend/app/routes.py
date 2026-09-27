"""Photo/video → MediaPipe → LightGBM → fixed JSON feedback."""
import logging
from contextlib import closing
from threading import Lock
from typing import Dict, List

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from models.lightgbm_loader import LightGBMLoader
from models.feedback_loader import load_feedback
from utils.normalizer import Normalizer
from utils.pose_comparison import PoseComparison
from utils.pose_rating import build_rating
from utils.pose_translator import PoseTranslator
from utils.feature_extractor import FeatureExtractor
from utils.pose_detector import PoseDetector, NoPoseDetected, MAX_IMAGE_BYTES
from utils.pose_visualization import render_prediction
from utils.pose_visualization import data_url
from utils.video_analysis import (
    analyze_video, FEEDBACK_INTERVAL_SECONDS, MAX_VIDEO_BYTES, SAMPLE_FPS,
    VideoLimitExceeded,
)

router = APIRouter(prefix="/api", tags=["Prediction"])
logger = logging.getLogger(__name__)
lightgbm_loader = LightGBMLoader()
feedback_generator = load_feedback()
normalizer = Normalizer()
pose_comparison = PoseComparison()
feature_extractor = FeatureExtractor()
pose_detector = PoseDetector()
prediction_lock = Lock()
UNRATED_FEEDBACK = "調整姿勢再重新拍攝"
POSE_CONFIDENCE_THRESHOLD = 0.3


class RatingResponse(BaseModel):
    score: float | None
    encouragement: str | None
    max_score: int
    hearts: float | None
    max_hearts: int
    correct_count: int
    detected_count: int
    total_count: int
    correct_ratio: float | None


class PredictionResponse(BaseModel):
    pose: str
    pose_en: str
    sub_pose: str
    sub_pose_en: str | None = None
    confidence: float
    center_type: str
    comparison: Dict
    rating: RatingResponse
    feedback: str
    suggestions: List[str]


class PhotoPredictionResponse(PredictionResponse):
    original_image: str
    skeleton_image: str
    image_width: int
    image_height: int
    landmarks: List[Dict]


class VideoFrameResponse(BaseModel):
    timestamp_seconds: float
    status: str
    reason: str | None = None
    original_image: str | None = None
    prediction: PhotoPredictionResponse | None = None
    is_feedback_frame: bool = False


class VideoPredictionResponse(BaseModel):
    sample_fps: int
    feedback_interval_seconds: float
    sampled_frames: int
    analyzed_frames: int
    unavailable_frames: int
    standard_frames: int
    nonstandard_frames: int
    indeterminate_frames: int
    frames: List[VideoFrameResponse]


@router.post("/predict-video", response_model=VideoPredictionResponse)
def predict_video(file: UploadFile = File(..., description="單人影片：MP4、MOV、WebM，最多 50 MiB、60 秒")):
    """Sample video at 2 FPS; preserve unavailable frames in the timeline."""
    try:
        file.file.seek(0, 2)
        size = file.file.tell()
        file.file.seek(0)
        if size > MAX_VIDEO_BYTES:
            raise HTTPException(status_code=413, detail="影片不可超過 50 MiB")
        if size == 0:
            raise ValueError("影片不可為空")
        frames = []
        next_feedback_time = 0.0
        # Closing explicitly also releases native resources if prediction raises.
        with closing(analyze_video(file.file)) as samples:
            for timestamp, content, landmarks, visibility, reason in samples:
                prediction = None
                if landmarks is not None:
                    try:
                        with prediction_lock:
                            result = _predict_landmarks(landmarks, visibility)
                        images = render_prediction(content, landmarks, visibility, result.comparison, pose_comparison.reference_poses.get(result.comparison.get("pose_name_zh")), output_format="JPEG")
                        prediction = PhotoPredictionResponse(**result.model_dump(), **images)
                    except NoPoseDetected:
                        reason = UNRATED_FEEDBACK
                if prediction is None:
                    reason = UNRATED_FEEDBACK
                is_feedback_frame = bool(
                    prediction is not None
                    and timestamp + 1e-9 >= next_feedback_time
                )
                if is_feedback_frame:
                    next_feedback_time = timestamp + FEEDBACK_INTERVAL_SECONDS
                frames.append(VideoFrameResponse(
                    timestamp_seconds=round(timestamp, 6),
                    status="analyzed" if prediction else "unavailable", reason=reason,
                    original_image=data_url(content, "image/jpeg") if prediction is None else None,
                    prediction=prediction, is_feedback_frame=is_feedback_frame,
                ))
        analyzed = [frame.prediction for frame in frames if frame.prediction is not None]
        return VideoPredictionResponse(
            sample_fps=SAMPLE_FPS, feedback_interval_seconds=FEEDBACK_INTERVAL_SECONDS,
            sampled_frames=len(frames), analyzed_frames=len(analyzed),
            unavailable_frames=len(frames) - len(analyzed),
            standard_frames=sum(p.comparison["is_standard"] is True for p in analyzed),
            nonstandard_frames=sum(p.comparison["is_standard"] is False for p in analyzed),
            indeterminate_frames=sum(p.comparison["is_standard"] is None for p in analyzed),
            frames=frames,
        )
    except HTTPException:
        raise
    except VideoLimitExceeded as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Video prediction failed")
        raise HTTPException(status_code=500, detail="影片分析失敗，請查看後端日誌") from exc
    finally:
        file.file.close()


@router.post("/predict", response_model=PhotoPredictionResponse)
def predict_pose(file: UploadFile = File(..., description="單人全身照片：JPEG、PNG 或 WebP，最多 10 MiB")):
    """上傳照片，由後端擷取 33 個關鍵點、分類姿勢並產生文字回饋。"""
    try:
        content = file.file.read(MAX_IMAGE_BYTES + 1)
        if len(content) > MAX_IMAGE_BYTES:
            raise HTTPException(status_code=413, detail="照片不可超過 10 MiB")
        landmarks, visibility = pose_detector.extract(content)
        # Sync endpoints use the worker pool. Serialize shared ML model inference.
        with prediction_lock:
            prediction = _predict_landmarks(landmarks, visibility)
        images = render_prediction(content, landmarks, visibility, prediction.comparison, pose_comparison.reference_poses.get(prediction.comparison.get("pose_name_zh")))
        return PhotoPredictionResponse(**prediction.model_dump(), **images)
    except HTTPException:
        raise
    except NoPoseDetected as exc:
        raise HTTPException(status_code=422, detail=UNRATED_FEEDBACK) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Photo prediction failed")
        raise HTTPException(status_code=500, detail="照片分析失敗，請查看後端日誌") from exc
    finally:
        file.file.close()


def _predict_landmarks(landmarks, visibility):
    normalized, center_type = normalizer.normalize(landmarks, visibility=visibility)
    if center_type == "none":
        raise NoPoseDetected("人體關鍵點不足以分析，請上傳清楚的全身照片")
    features = feature_extractor.extract_features(normalized)
    pose, sub_pose, confidence = lightgbm_loader.predict(features)
    pose_en = PoseTranslator.translate_to_english(pose)
    sub_pose_en = PoseTranslator.translate_to_english(sub_pose) if sub_pose else None
    comparison = pose_comparison.compare(pose, landmarks, visibility=visibility)
    feedback, suggestions = feedback_generator.generate(
        pose=pose, pose_en=pose_en, sub_pose=sub_pose, sub_pose_en=sub_pose_en,
        comparison=comparison, confidence=confidence,
    )
    rating = build_rating(comparison)
    if confidence <= POSE_CONFIDENCE_THRESHOLD:
        pose, pose_en, sub_pose, sub_pose_en = "尚無法辨識", "", "", ""
        feedback, suggestions = "尚無法辨識", []
        comparison = dict(comparison, pose_name_zh="", pose_name_en="",
                          overall_assessment="尚無法辨識")
    if rating["score"] is None:
        pose = pose_en = sub_pose = sub_pose_en = ""
        feedback, suggestions = UNRATED_FEEDBACK, []
        comparison = dict(comparison, pose_name_zh="", pose_name_en="",
                          overall_assessment=UNRATED_FEEDBACK)
    return PredictionResponse(
        pose=pose, pose_en=pose_en or "", sub_pose=sub_pose,
        sub_pose_en=sub_pose_en, confidence=float(confidence), center_type=center_type,
        comparison=comparison, feedback=feedback, suggestions=suggestions,
        rating=rating,
    )
