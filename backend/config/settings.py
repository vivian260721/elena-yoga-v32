"""Runtime settings used by the prediction API."""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

LIGHTGBM_MODEL_PATH = os.getenv("LIGHTGBM_MODEL_PATH", "Model/anglediff_lightgbm.joblib")
FEEDBACK_JSON_PATH = os.getenv("FEEDBACK_JSON_PATH", "data/pose_feedback_fix.json")
REFERENCE_POSES_PATH = os.getenv("REFERENCE_POSES_PATH", "utils/yoga_5poses_mediapipe_dataset_complete.csv")

CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS", "http://localhost:8080,http://127.0.0.1:8080"
    ).split(",")
    if origin.strip()
]
CORS_ALLOW_CREDENTIALS = os.getenv("CORS_ALLOW_CREDENTIALS", "False").lower() == "true"
CORS_ALLOW_METHODS = ["GET", "POST", "PUT", "DELETE"]
CORS_ALLOW_HEADERS = ["*"]
