"""
lotus_score.py
===============
一朵蓮花＝1 分，半朵＝0.5 分，以此類推
給 result_display_card.py 使用。
"""

_LOTUS_IMAGES = {
    1.0:"/static/images/lotus_parts/part_1.png",
    0.5:"/static/images/lotus_parts/part_2.png",
    0.0:"/static/images/lotus_parts/part_3.png",
}

# ============================================================
# 單朵蓮花
# ============================================================

def _lotus_image(fill_level: float) -> str:
    """
    fill_level:
        0.0 -> 空
        0.5 -> 半朵
        1.0 -> 滿朵
    """

    # 確保只接受 0 / 0.5 / 1
    fill_level = max(0.0, min(1.0, fill_level))

    # 避免浮點數造成 dictionary key 找不到
    fill_level = round(fill_level * 2) / 2

    image_path = _LOTUS_IMAGES[fill_level]

    return (
        f'<img '
        f'src="{image_path}" '
        f'class="lotus-icon" '
        f'alt="lotus">'
    )


# ============================================================
# 產生 5 朵蓮花
# ============================================================

def render_lotus_row(
    score: float,
    max_lotus: int = 5,
) -> str:

    # 限制分數在 0~5
    score = max(0.0, min(float(max_lotus), float(score)))

    # 只允許 0.5 的級距
    score = round(score * 2) / 2

    icons = []

    for i in range(max_lotus):
        remaining = score - i

        if remaining >= 1.0:
            fill_level = 1.0

        elif remaining >= 0.5:
            fill_level = 0.5

        else:
            fill_level = 0.0

        icons.append(
            _lotus_image(fill_level)
        )

    score_text = f"{score:g} / {max_lotus}"
    
    return (
        f'<div class="lotus-score-block">'
        f'<div class="lotus-row">{"".join(icons)}'
        f'<div class="lotus-score-text">{score_text}</div>'
        f"</div></div>"
    )