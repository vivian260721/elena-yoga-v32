"""
camera_capture.py
==================
Component（純函式，不用 class）：對應需求「使用裝置」按鈕直接啟動裝置相機，
可以選擇拍照或錄影，結束後自動送去分析。

對應需求「透過判斷裝置是否有鏡頭顯示使用裝置按鈕」：頁面載入時用 JS 的
navigator.mediaDevices.enumerateDevices() 檢查裝置是否有攝影機，
沒有鏡頭（例如桌機沒接鏡頭、或瀏覽器不支援）就不顯示這顆按鈕，不會讓使用者點了才發現不能用。

對應需求「前端不存實體檔」：拍照/錄影拿到的內容全程只放在記憶體 bytes，不寫進前端磁碟。

流程：偵測到鏡頭 -> 顯示「使用裝置」按鈕 -> 按下後彈窗開啟相機預覽 -> 選「拍照」或
「開始/停止錄影」-> 擷取到的內容轉成記憶體 bytes -> 自動呼叫 on_captured callback
（不需要使用者再按送出，直接觸發分析 API）。
"""
import base64
from nicegui import ui


def build_device_capture_button(on_captured, render_trigger=None):
    """
    建立相機拍攝彈窗，並在偵測到裝置有攝影機時顯示觸發按鈕。
    on_captured(file_bytes, filename, content_type) 會在拍照/錄影完成的當下立即被呼叫，
    呼叫端（main.py / upload_section.py）應該直接觸發分析，不需要等使用者再按一次送出。

    render_trigger(open_camera_dialog, container)：選填，讓呼叫端自訂「使用裝置」的觸發元件外觀
    （例如做成參考圖裡的「Recommended」卡片樣式），預設不提供的話就顯示一顆普通按鈕。
    """
    ui.add_head_html('<script src="/static/js/camera.js"></script>')

    button_container = ui.column().classes("device-capture-container")

    with ui.dialog() as dialog, ui.card().classes("camera-dialog-card"):
        ui.label("使用裝置拍攝").classes("section-title")
        ui.html('<video id="camera-preview" autoplay playsinline muted class="camera-preview"></video>')
        ui.html('<canvas id="camera-canvas" style="display:none;"></canvas>')

        status_label = ui.label("").classes("camera-status-text")
        record_state = {"recording": False}

        async def save_and_dispatch(data_url: str, ext: str, mime: str) -> None:
            """把拿到的 base64 資料轉成記憶體 bytes（不落地存檔），關掉相機/彈窗，並立刻觸發分析"""
            _, b64_data = data_url.split(",", 1)
            file_bytes = base64.b64decode(b64_data)
            filename = f"camera_capture.{ext}"

            await ui.run_javascript("stopCamera()")
            dialog.close()
            ui.notify("已擷取，開始分析…", type="positive")
            await on_captured(file_bytes, filename, mime)

        async def handle_photo():
            data_url = await ui.run_javascript("capturePhoto()", timeout=10.0)
            if not data_url:
                ui.notify("拍照失敗，請確認已允許鏡頭權限", type="negative")
                return
            await save_and_dispatch(data_url, "jpg", "image/jpeg")

        async def handle_record_toggle():
            if not record_state["recording"]:
                await ui.run_javascript("startRecording()")
                record_state["recording"] = True
                record_btn.props("color=negative")
                record_btn.set_text("停止錄影")
                status_label.set_text("錄影中…")
                return

            # 停止錄影：等待瀏覽器把錄好的內容編碼成 base64，影片較長時可能要等幾秒
            status_label.set_text("處理中…")
            data_url = await ui.run_javascript("stopRecording()", timeout=30.0)
            record_state["recording"] = False
            record_btn.props(remove="color=negative")
            record_btn.set_text("開始錄影")
            status_label.set_text("")

            if not data_url:
                ui.notify("錄影失敗，請確認已允許鏡頭權限", type="negative")
                return
            await save_and_dispatch(data_url, "webm", "video/webm")

        with ui.row().classes("camera-controls-row"):
            ui.button("拍照", icon="camera", on_click=handle_photo).classes("primary-btn")
            record_btn = ui.button(
                "開始錄影", icon="fiber_manual_record", on_click=handle_record_toggle
            ).classes("secondary-btn")

    async def open_camera_dialog():
        dialog.open()
        await ui.run_javascript("startCamera()")

    def handle_camera_availability(e):
        has_camera = bool(e.args.get("hasCamera"))
        if not has_camera:
            return
        with button_container:
            if render_trigger:
                render_trigger(open_camera_dialog)
            else:
                ui.button("使用裝置", icon="videocam", on_click=open_camera_dialog).classes(
                    "primary-btn device-capture-button"
                )

    ui.on("camera_availability_result", handle_camera_availability)
    ui.timer(0.3, lambda: ui.run_javascript("checkCameraAvailability()"), once=True)

    return button_container
