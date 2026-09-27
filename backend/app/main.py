"""
FastAPI 主應用 - Yoga Pose Analysis System
負責應用初始化和服務運行
"""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import router, lightgbm_loader, pose_detector
from config import settings

# 創建 FastAPI 應用
app = FastAPI(
    title="Yoga Pose Analysis API",
    description="上傳照片，由後端 MediaPipe 擷取關鍵點，使用 LightGBM 分析瑜伽姿勢並提供固定 JSON 回饋",
    version="1.0.0"
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
)

# 包含路由
app.include_router(router)
logging.getLogger("uvicorn.error").info(
    "Classification model loaded: %s (%d features)",
    lightgbm_loader.model_path.resolve(), lightgbm_loader.model.n_features_in_,
)
logging.getLogger("uvicorn.error").info(
    "Landmark model: %s", pose_detector.model_path.resolve(),
)


@app.get("/")
async def root():
    """根路由 - API 狀態檢查"""
    return {"message": "Yoga Pose Analysis API is running"}


@app.get("/health")
async def health_check():
    """健康檢查端點"""
    return {"status": "healthy", "landmark_model": pose_detector.model_path.name, "classifier": {
        "model": lightgbm_loader.model_path.name,
        "features": lightgbm_loader.model.n_features_in_,
        "loaded": lightgbm_loader.is_loaded,
    }}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
