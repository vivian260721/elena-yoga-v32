"""
message_banner.py
==================
Component（純函式）：共用的訊息顯示區塊，取代原本散落在各元件裡各自的
ui.notify()（跳出式 toast，幾秒後自動消失）。

用 NiceGUI 元素的 .visible 屬性控制顯示/隱藏 —— 背後是用 CSS 隱藏（v-show），
元件本身「一直都在」DOM 裡，只是切換 hidden 樣式，不會整個重新建立/拆除，
切換時沒有畫面閃爍或版面跳動，適合放「處理中」「上傳失敗」這種需要持續顯示、
使用者看得到才會消失的訊息（跟 ui.notify 的「一閃即逝」用途不同）。
"""
from nicegui import ui

_ICON_BY_KIND = {
    "info": "info",
    "success": "check_circle",
    "warning": "warning",
    "error": "error",
}
_CLASS_BY_KIND = {
    "info": "message-banner-info",
    "success": "message-banner-success",
    "warning": "message-banner-warning",
    "error": "message-banner-error",
}


def build() -> dict:
    """
    建立一個共用訊息區塊，預設隱藏。
    回傳 {"show": show_fn, "hide": hide_fn}，呼叫端保存這個 dict，
    之後在任何地方呼叫 banner["show"]("訊息文字", "error") / banner["hide"]() 即可控制這塊區域。
    """
    with ui.row().classes("message-banner") as banner:
        icon = ui.icon("info").classes("message-banner-icon")
        label = ui.label("").classes("message-banner-text")

    banner.visible = False  # 初始隱藏，用 .visible 而非移除元件，避免版面跳動

    def show(text: str, kind: str = "info") -> None:
        """顯示訊息區塊。kind: 'info' / 'success' / 'warning' / 'error'，決定顏色與 icon"""
        icon.set_name(_ICON_BY_KIND.get(kind, "info"))
        label.set_text(text)
        banner.classes(remove=" ".join(_CLASS_BY_KIND.values()))
        banner.classes(add=_CLASS_BY_KIND.get(kind, "message-banner-info"))
        banner.visible = True

    def hide() -> None:
        """隱藏訊息區塊（元件還在 DOM 裡，只是用 CSS 隱藏，下次 show() 直接重新顯示）"""
        banner.visible = False

    return {"show": show, "hide": hide}
