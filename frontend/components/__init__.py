"""
components 套件
================
所有元件都是「純函式」（不用 class），呼叫端直接用 build_xxx() 組出畫面。
這個 __init__.py 統一 re-export 常用函式，方便 main.py 用簡短的方式 import。
"""
from .nav_bar import build as build_nav_bar
from .footer import build as build_footer
from .hero_section import build as build_hero_section
from .marquee_slider import build as build_marquee_slider
from .pose_carousel import build as build_pose_carousel
from .upload_section import build as build_upload_section
from .camera_capture import build_device_capture_button
from .lotus_score import render_lotus_row
from .message_banner import build as build_message_banner
from .loading_screen import build as build_loading_screen
from . import result_display_card
from .cursor_wheel import CursorWheel

__all__ = [
    "build_nav_bar",
    "build_footer",
    "build_hero_section",
    "build_marquee_slider",
    "build_pose_carousel",
    "build_upload_section",
    "build_device_capture_button",
    "render_lotus_row",
    "build_message_banner",
    "build_loading_screen",
    "result_display_card",
    "CursorWheel",
]
