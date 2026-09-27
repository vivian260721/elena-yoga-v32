"""Load the fixed JSON phrase bank used by photo and video feedback."""
from config import settings
from utils.json_feedback import JsonFeedback


def load_feedback():
    return JsonFeedback(settings.FEEDBACK_JSON_PATH)
