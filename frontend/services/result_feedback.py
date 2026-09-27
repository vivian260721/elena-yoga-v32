UNRATED_FEEDBACK = "調整姿勢再重新拍攝"


def normalize_result(result):
    """Copy for presentation; classification and feedback belong to the API."""
    return dict(result)
