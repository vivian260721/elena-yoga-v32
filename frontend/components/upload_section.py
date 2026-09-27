"""
upload_section.py
==================
"""
from nicegui import ui, events

from components import camera_capture


def build(on_file_selected, on_captured, on_submit):
    """
    建立整個 Upload 區塊。
    on_file_selected(file_bytes, filename, content_type)：選檔完成時呼叫（不會自動分析）
    on_captured(file_bytes, filename, content_type)：拍照/錄影完成時呼叫（呼叫端應直接觸發分析）
    on_submit()：點擊開始分析
    """
    ui.add_head_html('<script src="/static/js/upload_dropzone.js"></script>')
   
    with ui.column().classes("upload-outer-box"):
        ui.label("Upload").classes("upload-box-title")

        
        with ui.row().classes("upload-inner-row"):
            # ---- 左側：你的自訂拖放區 ----
            with ui.column().classes("upload-dropzone"):
                ui.icon("cloud_upload").classes("upload-icon")
                ui.label("點擊或將檔案拖曳至此上傳").classes("upload-title")
                ui.label("照片最多 10 MiB，影片最多 50 MiB／60 秒").classes("upload-subtitle")
                ui.label("支援 JPG、PNG、WebP、MP4、MOV、WebM").classes("upload-subtitle")
                selected_label = ui.label("").classes("upload-selected-text")

                async def handle_upload(e: events.UploadEventArguments):
                    try:
                        file_bytes = await e.file.read()

                        on_file_selected(
                            file_bytes,
                            e.file.name,
                            e.file.content_type or "application/octet-stream",
                        )
                        selected_label.set_text(f"已選擇：{e.file.name}")
                        ui.notify(f"已選擇檔案：{e.file.name}", type="positive")
                    except Exception as err:
                        ui.notify(f"讀取檔案失敗：{err}", type="negative")

                # 背景隱藏的標準上傳元件（接收來自 JS 轉交的檔案）
                ui.upload(
                    label="",
                    on_upload=handle_upload,
                    on_rejected=lambda: ui.notify("檔案格式或大小不符合限制", type="negative"),
                    auto_upload=True,
                    max_file_size=50 * 1024 * 1024,
                ).props('accept=".jpg,.jpeg,.png,.webp,.mp4,.mov,.webm" hide-upload-btn')

            
            # ---- 右側：captured 按鈕（使用裝置）+ Browse My Device 按鈕（選檔）----
            with ui.column().classes("upload-side-column"):
                async def handle_submit_click():
                    submit_btn.props("loading")
                    try:
                        await on_submit()
                    finally:
                        submit_btn.props(remove="loading")
        
                submit_btn = ui.button("開始分析", icon="analytics", on_click=handle_submit_click).classes("!bg-[#7FA192] browse-device-button")
                 
                def render_captured_trigger(open_camera_dialog):
                    with ui.card().on("click", open_camera_dialog).classes("captured-btn"):
                        ui.label("使用裝置拍照/錄影").classes("captured-label")
                        ui.icon('camera_alt').classes("captured-icon text-5xl")
                       
                camera_capture.build_device_capture_button(
                    on_captured=on_captured, render_trigger=render_captured_trigger
                )
