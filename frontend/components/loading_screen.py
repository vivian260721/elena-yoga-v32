"""
loading_screen.py
==================
Component（純函式）：分析中的載入畫面，對應需求版面順序
「影片 slider → 上傳框 → loading 畫面 → review」中的第三塊。

用 .visible 控制顯示/隱藏（元件一直在 DOM 裡，只是切換 CSS 顯示狀態），
跟 message_banner.py 同一種寫法，但這個專門給「分析中」這個狀態用，固定有 spinner 圖示。
"""
from nicegui import ui


def build() -> dict:
    """建立載入畫面，回傳 {"show": show_fn, "hide": hide_fn}"""
    with ui.column().classes("loading-screen") as screen:
        ui.spinner(size="lg").classes("loading-spinner")
        text_label = ui.label("分析中，請稍候…").classes("loading-text")

    screen.visible = False

    def show(text: str = "分析中，請稍候…") -> None:
        text_label.set_text(text)
        screen.visible = True

    def hide() -> None:
        screen.visible = False

    return {"show": show, "hide": hide}
