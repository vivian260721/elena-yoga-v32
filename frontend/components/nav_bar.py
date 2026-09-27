"""
nav_bar.py
==========
"""
from nicegui import ui



def build(active: str = "home") -> None:
   
    with ui.row().classes("nav-bar"):
        with ui.row().classes("nav-brand"):
            ui.label("Elena ❤ YOGA").classes("nav-brand-text")
        

        nav_items = [
            ("Home", "/", "home"),
            ("線上分析", "/analyze", "analyze"),
            # ("即時分析", "/realtime", "realtime"),
        ]

        with ui.row().classes("nav-links"):
            for text, path, name in nav_items:
                classes = "nav-link nav-link--active" if active == name else "nav-link"
                ui.link(text, path).classes(classes)
