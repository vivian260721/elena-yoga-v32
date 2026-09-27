"""Elena YOGA：照片與影片姿勢分析介面。"""
from pathlib import Path
import os
from nicegui import ui, app

import components
from services import api_client
from services.video_timeline import frame_view
from services.result_feedback import UNRATED_FEEDBACK

STATIC_DIR = Path(__file__).resolve().parent / "static"
app.add_static_files("/static", str(STATIC_DIR))


def _head():
    ui.add_head_html('<link rel="stylesheet" href="/static/css/style.css">')


@ui.page("/")
async def home_page():
    _head()
    components.build_nav_bar(active="home")
    components.CursorWheel(k=8, mode='trail')
    with ui.row().classes("page-container"):
        components.build_hero_section()
        components.build_marquee_slider()
    components.build_footer()


@ui.page("/analyze")
async def practice_page():
    _head()
    components.build_nav_bar(active="analyze")
    components.CursorWheel(k=6)

    with ui.column().classes("page-container"):
        components.build_pose_carousel()
        video_frames: list[dict] = []
        pending_upload = {"bytes": None, "name": None, "type": None}
        analyzing = False

        def show_video_frame(index: int):
            if not video_frames:
                return
            index = max(0, min(index, len(video_frames) - 1))
            result, feedback_time = frame_view(video_frames, index)
            timestamp = video_frames[index]["timestamp_seconds"]
            
            result["max_frames"] = len(video_frames) - 1
            result["current_frame_index"] = index
            result["frame_text"] = f"影片 {timestamp:.2f} 秒 · 影格 {index + 1} / {len(video_frames)}"
            result["feedback_time"] = feedback_time

            components.result_display_card.build(
                result_container, 
                result, 
                is_video=True,
                on_slider_change=show_video_frame
            )

        async def run_analysis(file_bytes: bytes, filename: str, content_type: str):
            nonlocal video_frames, analyzing
            if analyzing:
                ui.notify("分析進行中，請稍候", type="warning")
                return
            analyzing = True
            video_frames = []
            result_container.clear()
            loading["show"]("分析中，請稍候…")
            is_video = content_type.startswith("video/") or filename.lower().endswith(
                (".mp4", ".mov", ".webm")
            )
            try:
                response = await api_client.analyze_media(
                    file_bytes=file_bytes, filename=filename,
                    is_video=is_video, content_type=content_type,
                )
                if is_video:
                    video_frames = response["frames"]
                    if not video_frames:
                        raise RuntimeError("影片沒有可顯示的影格")
                    show_video_frame(0)
                    ui.notify("分析完成", type="positive")
                else:
                    components.result_display_card.build(result_container, response)
                    ui.notify("分析完成", type="positive")
            except Exception as exc:
                video_frames = []
                result_container.clear()
                if str(exc) == UNRATED_FEEDBACK:
                    components.result_display_card.build(result_container, {
                        "rating": None, "feedback": UNRATED_FEEDBACK,
                    })
                else:
                    ui.notify(f"分析失敗：{exc}", type="negative")
            finally:
                analyzing = False
                loading["hide"]()

        def on_file_selected(file_bytes: bytes, filename: str, content_type: str):
            pending_upload.update(bytes=file_bytes, name=filename, type=content_type)

        async def submit_selected_file():
            if not pending_upload["bytes"]:
                ui.notify("請先選擇要上傳的照片或影片", type="warning")
                return
            await run_analysis(
                pending_upload["bytes"], pending_upload["name"], pending_upload["type"]
            )

        components.build_upload_section(
            on_file_selected=on_file_selected,
            on_captured=run_analysis,
            on_submit=submit_selected_file,
        )
        loading = components.build_loading_screen()
        
        result_container = ui.column().classes("result-container")

    components.build_footer()



if __name__ in {"__main__", "__mp_main__"}:
    ui.run(title="Elena ❤ YOGA", host="0.0.0.0", port=8080,
           reload=os.getenv("YOGA_RELOAD", "true").lower() == "true",
           show=False)
