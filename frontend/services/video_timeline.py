"""依目前影格選取畫面及最近一次排定的文字回饋。"""
from services.result_feedback import normalize_result


def frame_view(frames: list[dict], index: int) -> tuple[dict, str]:
    if not frames:
        raise ValueError("影片沒有可顯示的影格")
    index = max(0, min(index, len(frames) - 1))
    frame = frames[index]
    prediction = frame.get("prediction")
    result = dict(prediction) if prediction else {
        "pose": "",
        "original_image": frame.get("original_image"),
        "rating": None,
        "reason": None,
        "feedback": frame.get("reason") or "此影格無法分析",
        "suggestions": [],
    }
    if (result.get("rating") or {}).get("score") is None:
        return normalize_result(result), ""
    result["feedback"] = "等待第一個可分析影格的回饋…"
    result["suggestions"] = []
    feedback_time = ""
    for previous in reversed(frames[:index + 1]):
        if (previous.get("is_feedback_frame") and previous.get("prediction")
                and (previous["prediction"].get("rating") or {}).get("score") is not None):
            result["feedback"] = previous["prediction"].get("feedback", "")
            result["suggestions"] = previous["prediction"].get("suggestions", [])
            feedback_time = f"建議更新時間：{previous['timestamp_seconds']:.2f} 秒"
            break
    return normalize_result(result), feedback_time
