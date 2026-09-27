"""Deterministic corrections from measured joint angles, without invented degrees."""

JOINT_NAMES = {
    "L_elbow_angle": "左肘", "R_elbow_angle": "右肘",
    "L_shoulder_angle": "左肩", "R_shoulder_angle": "右肩",
    "L_hip_angle": "左髖", "R_hip_angle": "右髖",
    "L_knee_angle": "左膝", "R_knee_angle": "右膝",
}


def build_angle_feedback(comparison, include_priority=True):
    """Return assessment and corrections targeting the reference, not its boundary."""
    corrections = []
    unavailable = []
    is_downdog = comparison.get("pose_name_zh") == "下犬式"
    for name, angle in comparison["angles"].items():
        joint = JOINT_NAMES[name]
        if angle["within_tolerance"] is None:
            unavailable.append(joint)
            continue
        if angle["within_tolerance"]:
            continue
        actual = angle["actual_deg"]
        target = angle["reference_deg"]
        adjustment = target - actual
        amount = abs(adjustment)
        increase = adjustment > 0
        side = joint[0]
        if "shoulder" in name:
            # A shoulder angle alone cannot establish screen/world up or down.
            action = (f"將{side}上臂相對軀幹再張開一些"
                      if increase else f"將{side}上臂往軀幹方向收回一些")
        elif "elbow" in name:
            action = (f"將{side}手臂再伸直一些，讓{joint}少彎一點"
                      if increase else f"將{joint}再彎曲一些，讓前臂靠近上臂")
        elif "knee" in name:
            action = (f"將{side}腿再伸直一些，讓{joint}少彎一點"
                      if increase else f"將{joint}再彎曲一些，不要把{side}腿伸得太直")
        else:
            action = (f"將軀幹與{side}大腿之間的夾角再增加一些（{joint}）"
                      if increase else f"將軀幹與{side}大腿之間的夾角再減少一些（{joint}）")
        message = f"{action}（角度約需{'增加' if increase else '減少'} {amount:.1f}°，目前 {actual:.1f}°，參考 {target:.1f}°）。"
        corrections.append((amount, message))
    corrections.sort(key=lambda item: item[0], reverse=True)
    suggestions = [message for _, message in corrections]
    if unavailable and not is_downdog:
        suggestions.append(f"請讓{'、'.join(unavailable)}及相鄰關節清楚入鏡後重新拍攝，目前無法計算調整角度。")
    if comparison["is_standard"] is True:
        suggestions = ["八個關節角度均在參考值 容許差（髖 ±30°、其餘 ±20°） 內，保持目前姿勢即可，無需額外調整角度。"]
    status = comparison["is_standard"]
    feedback = ("符合標準：目前姿勢的八個關節角度都在參考值 容許差（髖 ±30°、其餘 ±20°） 內，保持目前姿勢即可。"
                if status is True else "尚未符合標準：請依下方建議調整動作。"
                if status is False else "目前無法判定是否符合標準：部分關節不清楚，請調整拍攝位置後再試一次。")
    if is_downdog:
        if status is True:
            feedback = "符合標準：下犬式可見側的關節角度均在容許差內（髖 ±30°、其餘 ±20°），保持目前姿勢即可。"
            suggestions = ["可見側角度符合標準，無需額外調整角度；側面拍攝時，另一側被遮住不影響本次評估。"]
        elif status is False:
            feedback = "下犬式可見關節尚未符合標準：請依下方建議調整動作。"
        else:
            feedback = "下犬式採側面評估，請讓同一側的肩、肘、腕、髖、膝、踝完整入鏡。"
            suggestions = ["維持側面拍攝，讓靠近鏡頭的一側完整入鏡即可，不需要同時露出左右兩側。"]
    if corrections and include_priority:
        feedback += f"有 {len(corrections)} 個部位需要調整，先從「{suggestions[0].split('（')[0]}」開始。"
    return feedback, suggestions
