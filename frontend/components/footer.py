"""
footer.py
=========
Component（純函式）：頁尾，樣式對齊參考圖（聯絡資訊 + 社群圖示 + Email 訂閱 + 條款連結）。
首頁與練習頁共用。
"""
from nicegui import ui


def build() -> None:
    with ui.row().classes("site-footer"):
        ui.label("Copyright © 2026 Elena Yoga | Powered by NiceGUI").classes("footer-contact")

        with ui.row().classes("footer-right"):
            ui.link('Home', '/').classes("footer-link no-underline")
            ui.link('線上分析', '/analyze').classes("footer-link no-underline")
            # ui.label("即時分析").classes("footer-link no-underline")

    