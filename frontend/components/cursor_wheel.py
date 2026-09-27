import os
import random
from nicegui import ui

class CursorWheel(ui.element):
    """
    k 顯示數量
    mode('orbit' 或 'trail')
    """
    def __init__(self, k=6, mode='orbit'):  # 預設摩天輪
        super().__init__('div')
        self.classes('pointer-events-none fixed inset-0 z-50')
        
        urls = self._get_random_images(k)
        if not urls:
            return
            
        # 👈 這裡要把 mode 帶進 HTML 的 data-mode 屬性中
        html_content = f'<div id="cursor-wheel-root" data-mode="{mode}">'
        for i, url in enumerate(urls):
            html_content += f'<div class="ferris-item" style="background-image: url(\'{url}\');"></div>'
        html_content += '</div>'
        
        with self:
            ui.html(html_content)
            
        ui.add_head_html('<script src="/static/js/cursor_wheel.js"></script>')

    def _get_random_images(self, k):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        root_dir = os.path.dirname(current_dir)
        images_dir_path = os.path.join(root_dir, 'static', 'images','icon')
        
        if not os.path.exists(images_dir_path):
            return []
            
        valid_ext = {'.png', '.jpg', '.jpeg', '.webp', '.gif'}
        try:
            all_files = [
                f for f in os.listdir(images_dir_path)
                if os.path.isfile(os.path.join(images_dir_path, f)) and
                os.path.splitext(f)[1].lower() in valid_ext
            ]
        except Exception:
            return []
            
        if not all_files:
            return []
            
        sampled = random.sample(all_files, min(k, len(all_files)))
        return [f'/static/images/icon/{f}' for f in sampled]
