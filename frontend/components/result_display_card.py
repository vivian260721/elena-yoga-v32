"""
result_display_card.py
========================
四欄：Original Image / Analysis Visualization / Alignment Score / Personalized Suggestions。
顯示單人照片或目前影片影格的分析。

Alignment Score 用蓮花燈號: 一朵＝1分、半朵＝0.5分。
"""
from nicegui import ui

from components.lotus_score import render_lotus_row
from services.result_feedback import normalize_result

def build(
    result_container: ui.column,
    analysis_response: dict,
    is_video=False,
    include_feedback=True,
    on_slider_change=None,  # 接收時間軸滑動時的 callback
):
    analysis_response = normalize_result(analysis_response)
    result_container.clear()

    with result_container:
        
        with ui.card().classes("pose-result-card"):
            ui.label("姿勢分析結果").classes("pose-result-title")

            if analysis_response.get("reason"):
                ui.label(analysis_response["reason"]).classes("result-error-text")
            
            with ui.row().classes("pose-result-columns"):
                # ---- 欄 1：Original Image ----
                with ui.column().classes("pose-result-col"):
                    ui.label("原始").classes("pose-result-col-header")
                    if analysis_response.get("original_image") and not is_video:
                        ui.image(analysis_response.get("original_image")).classes("pose-result")
                    elif analysis_response.get("original_image") and is_video:
                        ui.image(analysis_response.get("original_image"))
                    else:
                        ui.icon("image").classes("pose-result-thumb-placeholder")

                # ---- 欄 2：Analysis Visualization ----
                with ui.column().classes("pose-result-col"):
                    ui.label("分析").classes("pose-result-col-header")
                    if analysis_response.get("skeleton_image") and is_video:
                        ui.image(analysis_response.get("skeleton_image"))
                    elif analysis_response.get("skeleton_image") and not is_video:
                        ui.image(analysis_response.get("skeleton_image")).classes("pose-result")
                    else:
                        ui.icon("accessibility_new").classes("pose-result-thumb-placeholder")
                    ui.label("綠點：角度合格｜紅點：相關角度超標｜螢光藍色粗實線：正確角度連線，相鄰關節同時超標時合併為四點連線（達容忍範圍即消失）").classes("text-sm text-gray-600")

            if is_video:
                # ---- 欄 3：影片時間軸 ----
                with ui.column().classes("pose-result-columns !gap-0") as timeline_section:
                    frame_label = ui.label(analysis_response.get("frame_text", ""))
                    max_val = analysis_response.get("max_frames", 0)
                    current_val = analysis_response.get("current_frame_index", 0)
                    timeline = ui.slider(
                        min=0, max=max_val, step=1, value=current_val
                    ).classes("w-full").props('color=teal aria-label="影片時間軸"')
                    
                    if on_slider_change:
                        timeline.on_value_change(lambda e: on_slider_change(int(e.value)))
                        
                    feedback_time_label = ui.label(
                        analysis_response.get("feedback_time", "")
                    ).classes("text-sm text-gray-600")

            # ---- 欄 4：Score ----
            with ui.row().classes("pose-result-columns"):
                with ui.column().classes("pose-result-col"):
                    ui.label("分數").classes("pose-result-col-header")
                    rate = analysis_response.get("rating") 
                    count = rate.get("score") if rate else None
                    message = rate.get("encouragement") if count is not None else None
                    if count is None:
                        ui.label("無法評分")
                    else:
                        ui.html(render_lotus_row(count))
                        ui.label(message or "").classes("lotus-text")

            # ---- 欄 5：Personalized Suggestions ----
            with ui.row().classes("pose-result-columns"):
                with ui.column().classes("pose-result-col pose-result-col--suggestions"):
                    ui.label("個人化建議").classes("pose-result-col-header")
                    if analysis_response.get("pose"):
                        ui.label(analysis_response["pose"]).classes("pose-result-title")
                    with ui.column().classes("pose-suggestions-list"):
                        if include_feedback or count is None:
                            ui.label(analysis_response.get("feedback", "")).classes("pose-suggestion-item")
                                        
                        suggestion = analysis_response.get("suggestions", "")
                        if suggestion:
                            for text in suggestion:
                                ui.label(f"• {text}").classes("pose-suggestion-item")
                           
        #     error = person.get("error")
        #     if error:
        #         ui.label(error).classes("result-error-text")
