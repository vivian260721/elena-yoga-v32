"""
hero_section.py
================
"""
from nicegui import ui

def build() -> None:
    
    with ui.column().classes("w-full items-center mt-5 mb-5"):
        with ui.row().classes('w-full max-w-4xl items-center justify-center gap-8'):
            with ui.column().classes("hero-section w-full lg:w-1/2 max-w-2xl gap-5 order-1 max-lg:order-2"):
                ui.label("Hi, I'm Elena, \na Yoga Instructor...").classes("hero-title whitespace-pre-line")
                ui.label("只需上傳練習影像，系統便能精準分析您的瑜珈姿勢是否標準，協助您調整動作。").classes("hero-subtitle")
                ui.link("前往線上分析", "/analyze").classes("hero-cta-button")
            with ui.column().classes('w-56 h-80 lg:w-72 lg:h-96  ' \
                    'rounded-t-full overflow-hidden shadow-lg ' \
                    'border-2 border-dashed border-black p-1 lg:p-2 order-2 max-lg:order-1'):
                with ui.column().classes('w-full h-full object-cover rounded-t-full overflow-hidden'):
                    ui.image('../static/images/home.png').classes('w-full h-full justify-end')
