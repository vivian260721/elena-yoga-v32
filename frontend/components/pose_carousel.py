"""
pose_carousel.py
=================
左右卡片縮小當作預覽。改用 Swiper.js（CDN 載入）做 coverflow 特效，
支援滑鼠拖曳/手指滑動/慣性滾動，比純手刻 scroll-snap 更順滑。
"""
from nicegui import ui
from schemas import MediaCard

DEMO_POSES = [
    MediaCard(id="downdog", type="video", title="下犬式", desc="伸展脊椎與後腿肌群", tag="下犬式", url="/static/videos/demo_downdog.mp4"),
    
    MediaCard(id="tree", type="video", title="樹式", desc="訓練單腳平衡與專注力", tag="樹式", url="/static/videos/demo_tree.mp4"),
    MediaCard(id="plank", type="video", title="棒式", desc="強化核心與臀部肌群", tag="棒式", url="/static/videos/demo_plank.mp4"),
    MediaCard(id="goddess", type="video", title="女神式", desc="靈活膝蓋與緊緻雙腿", tag="女神式", url="/static/videos/demo_goddess.mp4"),
    MediaCard(id="warrior2", type="video", title="戰士二式", desc="強化下肢、開展髖部", tag="戰士二式", url="/static/videos/demo_warrior2.mp4"),
]

def build() :
    """
    建立姿勢選擇 Coverflow Carousel。
    回傳 state dict，state["centered_pose_id"] 會隨著滑動即時更新，保留給未來接上分析邏輯使用。
    """
    poses = DEMO_POSES
    state = {"centered_pose_id": poses[0].id if poses else None}
    default_index = min(2, len(poses) - 1) if poses else 0

    ui.add_head_html(
        '<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swiper@8/swiper-bundle.min.css">'
        '<script src="https://cdn.jsdelivr.net/npm/swiper@8/swiper-bundle.min.js"></script>'
        '<link rel="stylesheet" href="/static/css/pose_carousel.css">'
        '<script src="/static/js/pose_carousel.js"></script>'
    )

    with ui.element("div").classes("pose-carousel-stage"):
        with ui.element("div").classes("swiper pose-carousel").props(f'data-default-index="{default_index}"'):
            with ui.element("div").classes("swiper-wrapper"):
                for index, pose in enumerate(poses):
                    with ui.element("div").classes("swiper-slide"):
                        with ui.card().classes("pose-carousel-card").props(
                            f'data-slide-index="{index}" data-pose-id="{pose.id}" data-pose-name="{pose.title}"'
                        ):
                            ui.video(pose.url).classes("pose-carousel-video")
                            ui.label(pose.title).classes("pose-carousel-title")
                            if pose.desc:
                                ui.label(pose.desc).classes("pose-carousel-desc")
                            ui.label("CURRENT" if index == default_index else "SELECT").classes(
                                "pose-carousel-status"
                            )

    # def handle_center_change(e):
    #     pose_id = e.args.get("poseId")
    #     pose_name = e.args.get("poseName")
    #     state["centered_pose_id"] = pose_id
    #     # 目前僅 print 出來，尚未用於分析邏輯（對應需求：先印出來就好）
    #     print(f"[pose_carousel] 目前置中姿勢: {pose_name} ({pose_id})")

    # ui.on("pose_carousel_center_change", handle_center_change)

    # return state
