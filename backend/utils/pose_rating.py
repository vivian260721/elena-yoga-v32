"""Map correct joint counts to the pose-specific lotus rating tables."""
import json
from pathlib import Path
import random

from utils.pose_comparison import PoseComparison


ENCOURAGEMENTS = json.loads(
    (Path(__file__).resolve().parents[1] / "data" / "score_encouragement.json").read_text(
        encoding="utf-8"
    )
)

# Reuse the existing encouragement pools for the additional display levels.
ENCOURAGEMENTS["0"] = ENCOURAGEMENTS["1"]
ENCOURAGEMENTS["3.5"] = ENCOURAGEMENTS["3"]
ENCOURAGEMENTS["4.5"] = ENCOURAGEMENTS["4"]

OTHER_SCORES = (0, 1, 2, 3, 3.5, 4, 4, 4.5, 5)
DOWNDOG_SCORES = (0, 1, 3, 4.5, 5)


def build_rating(comparison):
    angles = comparison["angles"]
    statuses = [angles.get(name, {}).get("within_tolerance")
                for name in PoseComparison.ANGLE_JOINTS]
    is_downdog = comparison.get("pose_name_zh") == "下犬式"
    if is_downdog:
        sides = [[angles.get(f"{side}_{joint}_angle", {}).get("within_tolerance")
                  for joint in ("elbow", "shoulder", "hip", "knee")]
                 for side in ("L", "R")]
        statuses = max(sides, key=lambda values: (
            sum(value is not None for value in values), sum(value is True for value in values)))
    detected = sum(status is not None for status in statuses)
    correct = sum(status is True for status in statuses)
    score = (DOWNDOG_SCORES if is_downdog else OTHER_SCORES)[correct] if detected else None
    return {
        "score": score,
        "encouragement": random.choice(ENCOURAGEMENTS[str(score)]) if score is not None else None,
        "max_score": 5,
        "hearts": score,
        "max_hearts": 5,
        "correct_count": correct,
        "detected_count": detected,
        "total_count": len(statuses),
        "correct_ratio": correct / len(statuses) if detected else None,
    }
