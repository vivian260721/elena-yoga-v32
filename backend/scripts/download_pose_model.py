"""Download the official MediaPipe full pose model before starting the API."""
from pathlib import Path
from urllib.request import urlopen
import shutil
import tempfile

MODEL_URL = "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_full/float16/1/pose_landmarker_full.task"
DESTINATION = Path(__file__).resolve().parents[1] / "Model/pose_landmarker_full.task"


def main():
    if DESTINATION.is_file():
        print(f"Model already exists: {DESTINATION}")
        return
    DESTINATION.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with urlopen(MODEL_URL, timeout=120) as response:
            with tempfile.NamedTemporaryFile(dir=DESTINATION.parent, delete=False) as output:
                temporary = Path(output.name)
                shutil.copyfileobj(response, output)
        temporary.replace(DESTINATION)
        print(f"Downloaded: {DESTINATION}")
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
