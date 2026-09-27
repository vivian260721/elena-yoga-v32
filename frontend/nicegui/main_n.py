"""Minimal NiceGUI 3 frontend for the Yoga Backend API."""
import os

import httpx
from nicegui import events, ui

API_BASE_URL = os.getenv("YOGA_API_BASE_URL", "http://localhost:8000").rstrip("/")
REQUEST_TIMEOUT_SECONDS = 180.0


@ui.page("/")
def index() -> None:
    video_frames: list[dict] = []

    ui.label("瑜伽姿勢分析").classes("text-3xl font-bold")
    ui.label("上傳照片或短片，查看骨架、數字評分與調整建議。")
    status = ui.label("請選擇檔案")

    with ui.card().classes("w-full max-w-5xl"):
        with ui.row().classes("items-baseline gap-4"):
            pose = ui.label().classes("text-2xl font-bold")
            score = ui.label("尚未評分").classes("text-2xl text-pink-700")
        encouragement = ui.label().classes("text-lg font-semibold text-green-800")
        encouragement.set_visibility(False)
        rating_detail = ui.label("尚未評分")
        assessment = ui.label()

    with ui.row().classes("w-full max-w-5xl gap-4"):
        original = ui.image().classes("w-96")
        skeleton = ui.image().classes("w-96")

    feedback = ui.label().classes("text-lg")
    feedback_time = ui.label().classes("text-sm text-gray-600")
    suggestions = ui.column().classes("gap-1")
    timeline = ui.slider(min=0, max=0, value=0).classes("w-full max-w-5xl")
    timeline.set_visibility(False)

    def show_rating(rating: dict | None) -> None:
        count = rating.get("score") if rating else None
        message = rating.get("encouragement") if count is not None else None
        encouragement.set_text(message or "")
        encouragement.set_visibility(bool(message and message.strip()))
        if count is None:
            score.set_text("無法評分")
            rating_detail.set_text("無法評分")
            return
        maximum = rating["max_score"]
        score.set_text(f"{count} / {maximum} 分")
        rating_detail.set_text(
            f"正確 {rating['correct_count']}/{rating['detected_count']} 項"
            f"（{rating['correct_ratio'] * 100:.1f}%）"
        )

    def show_suggestions(items: list[str]) -> None:
        suggestions.clear()
        with suggestions:
            for text in items:
                ui.label(f"• {text}")

    def show_prediction(prediction: dict, *, include_feedback: bool = True) -> None:
        pose.set_text(prediction["pose"])
        assessment.set_text(prediction["comparison"]["overall_assessment"])
        show_rating(prediction.get("rating"))
        original.set_source(prediction["original_image"])
        skeleton.set_source(prediction["skeleton_image"])
        skeleton.set_visibility(True)
        if include_feedback:
            feedback.set_text(prediction["feedback"])
            feedback_time.set_text("")
            show_suggestions(prediction["suggestions"])

    def show_video_frame(index: int) -> None:
        if not video_frames:
            return
        index = max(0, min(index, len(video_frames) - 1))
        frame = video_frames[index]
        prediction = frame.get("prediction")
        if prediction:
            show_prediction(prediction, include_feedback=False)
        else:
            pose.set_text("無法判定")
            assessment.set_text(frame.get("reason") or "此影格無法分析")
            show_rating(None)
            original.set_source(frame["original_image"])
            skeleton.set_visibility(False)

        # 保留最近一則排定回饋；非回饋影格不清空文字。
        for previous in reversed(video_frames[:index + 1]):
            if previous["is_feedback_frame"] and previous.get("prediction"):
                result = previous["prediction"]
                feedback.set_text(result["feedback"])
                feedback_time.set_text(
                    f"此建議於影片 {previous['timestamp_seconds']:.2f} 秒更新"
                )
                show_suggestions(result["suggestions"])
                break
        else:
            feedback.set_text("等待第一個可分析影格的回饋…")
            feedback_time.set_text("")
            show_suggestions([])

    def on_timeline_change(event) -> None:
        show_video_frame(int(event.value))

    timeline.on_value_change(on_timeline_change)

    async def handle_upload(event: events.UploadEventArguments) -> None:
        nonlocal video_frames
        status.set_text("分析中，請稍候…")
        video_frames = []
        show_rating(None)
        score.set_text("尚未評分")
        rating_detail.set_text("分析中，請稍候…")
        timeline.set_visibility(False)
        try:
            content = await event.file.read()
            filename = event.file.name
            content_type = event.file.content_type or "application/octet-stream"
            is_video = content_type.startswith("video/") or filename.lower().endswith(
                (".mp4", ".mov", ".webm")
            )
            endpoint = "/api/predict-video" if is_video else "/api/predict"
            async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS) as client:
                response = await client.post(
                    f"{API_BASE_URL}{endpoint}",
                    files={"file": (filename, content, content_type)},
                )
            data = response.json()
            if response.is_error:
                detail = data.get("detail", "分析失敗") if isinstance(data, dict) else "分析失敗"
                raise RuntimeError(detail)

            if is_video:
                video_frames = data["frames"]
                timeline.props["max"] = max(0, len(video_frames) - 1)
                timeline.value = 0
                timeline.update()
                timeline.set_visibility(bool(video_frames))
                show_video_frame(0)
                status.set_text(
                    f"影片分析完成：取樣 {data['sampled_frames']} 張，"
                    f"文字回饋最短間隔 {data['feedback_interval_seconds']:.0f} 秒"
                )
            else:
                video_frames = []
                show_prediction(data)
                status.set_text("照片分析完成")
        except (httpx.HTTPError, RuntimeError, ValueError) as error:
            show_rating(None)
            status.set_text(f"分析失敗：{error}")
            ui.notify(str(error), type="negative")

    ui.upload(
        label="選擇照片或影片",
        on_upload=handle_upload,
        on_rejected=lambda: ui.notify("檔案格式或大小不符合限制", type="negative"),
        auto_upload=True,
        max_file_size=50 * 1024 * 1024,
    ).props("accept=.jpg,.jpeg,.png,.webp,.mp4,.mov,.webm").classes("w-full max-w-5xl")


ui.run(host="0.0.0.0", port=8080, title="瑜伽姿勢分析")
