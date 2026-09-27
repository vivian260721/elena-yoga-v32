"""Verify all runtime dependencies before starting Elena Yoga backend."""
import importlib
import sys

REQUIRED = [
    "fastapi", "uvicorn", "pydantic", "multipart", "numpy", "pandas",
    "lightgbm", "joblib", "sklearn", "mediapipe", "PIL", "av", "dotenv",
]

failed = []
for name in REQUIRED:
    try:
        importlib.import_module(name)
        print(f"[OK] {name}")
    except Exception as exc:
        failed.append((name, exc))
        print(f"[FAIL] {name}: {exc}")

if failed:
    print("\nDependency check FAILED. Re-run: python -m pip install -r requirements.txt")
    sys.exit(1)

print("\nAll backend dependencies are installed.")
