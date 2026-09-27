"""
marquee_slider.py
=================
"""
from nicegui import ui

def build():

    ui.add_head_html(
            '<link rel="stylesheet" href="/static/css/marquee_slider.css">'
    )
     # 單一外框容器 (同一道)
    with ui.element('div').classes('ultra-film-container'):
         with ui.element('div').classes('ultra-film-track'):
            ui.element('div').classes('film-section film-section-a')
            ui.element('div').classes('film-section film-section-b')
            ui.element('div').classes('film-section film-section-a')
            ui.element('div').classes('film-section film-section-b')
           

    
