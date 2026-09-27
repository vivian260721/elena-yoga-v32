"""透過 HTTP 上傳記憶體中的照片或影片，取得分析結果。"""
import os

import httpx


# 統一使用文件中的名稱，並保留舊設定的相容性。
API_BASE_URL = (
    os.getenv("YOGA_API_BASE_URL")
    or os.getenv("BACKEND_API_URL")
    or "http://localhost:8000"
).rstrip("/")
REQUEST_TIMEOUT_SECONDS = 180.0


async def analyze_media(
    file_bytes: bytes,
    filename: str,
    is_video: bool,
    content_type: str = "application/octet-stream",
) -> dict:
    endpoint = "/api/predict-video" if is_video else "/api/predict"
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS) as client:
        response = await client.post(
            f"{API_BASE_URL}{endpoint}",
            files={"file": (filename, file_bytes, content_type)},
        )
        if response.is_error:
            try:
                data = response.json()
            except ValueError:
                response.raise_for_status()
            detail = data.get("detail") if isinstance(data, dict) else None
            if detail:
                raise RuntimeError(str(detail))
            response.raise_for_status()
        return response.json()
