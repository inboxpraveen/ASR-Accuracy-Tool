import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
SEGMENTS_DIR = DATA_DIR / "segments"
EXPORT_DIR = DATA_DIR / "exports"
STATE_FILE = DATA_DIR / "transcriptions.csv"


class Config:
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "change-me")
    DEFAULT_MODEL = os.getenv("ASR_MODEL", "openai/whisper-small")


def ensure_directories() -> None:
    """Create runtime directories if missing."""
    for path in (DATA_DIR, SEGMENTS_DIR, EXPORT_DIR):
        path.mkdir(parents=True, exist_ok=True)

