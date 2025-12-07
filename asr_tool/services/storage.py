from __future__ import annotations

import uuid
from pathlib import Path
from threading import RLock
from typing import Dict, List

import pandas as pd

from asr_tool.config import EXPORT_DIR, STATE_FILE


_lock = RLock()
COLUMNS = ["id", "filename", "transcription", "correct_transcripts", "job_id", "locked", "locked_at"]


def _empty_df() -> pd.DataFrame:
    return pd.DataFrame(columns=COLUMNS)


def load_state() -> pd.DataFrame:
    with _lock:
        if Path(STATE_FILE).exists():
            return pd.read_csv(STATE_FILE)
        return _empty_df()


def save_state(df: pd.DataFrame) -> None:
    with _lock:
        df.to_csv(STATE_FILE, index=False)


def append_record(record: Dict) -> None:
    df = load_state()
    df = pd.concat([df, pd.DataFrame([record])], ignore_index=True)
    save_state(df)


def update_record(record_id: str, corrected_text: str) -> None:
    df = load_state()
    # Only allow updates if row is not locked
    mask = df["id"] == record_id
    if mask.any() and "locked" in df.columns:
        if df.loc[mask, "locked"].iloc[0]:
            raise ValueError("Record is locked and cannot be edited")
    df.loc[mask, "correct_transcripts"] = corrected_text
    save_state(df)


def lock_record(record_id: str) -> None:
    """Lock a record to prevent further edits."""
    df = load_state()
    if "locked" not in df.columns:
        df["locked"] = False
    if "locked_at" not in df.columns:
        df["locked_at"] = None
    
    mask = df["id"] == record_id
    df.loc[mask, "locked"] = True
    df.loc[mask, "locked_at"] = pd.Timestamp.now().isoformat()
    save_state(df)


def unlock_record(record_id: str) -> None:
    """Unlock a record to allow edits."""
    df = load_state()
    if "locked" not in df.columns:
        df["locked"] = False
    if "locked_at" not in df.columns:
        df["locked_at"] = None
    
    mask = df["id"] == record_id
    df.loc[mask, "locked"] = False
    df.loc[mask, "locked_at"] = None
    save_state(df)


def bulk_import(records: List[Dict]) -> None:
    df = load_state()
    df = pd.concat([df, pd.DataFrame(records)], ignore_index=True)
    save_state(df)


def export_records(fmt: str = "xlsx") -> Path:
    df = load_state()
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    if fmt == "csv":
        path = EXPORT_DIR / "transcriptions_export.csv"
        df.to_csv(path, index=False)
        return path
    path = EXPORT_DIR / "transcriptions_export.xlsx"
    df.to_excel(path, index=False)
    return path


def import_manual(chunk_folder: str, excel_path: str, job_id: str) -> List[Dict]:
    """Load an existing excel plus chunked audio folder into state."""
    df_excel = pd.read_excel(excel_path)
    required = {"filename", "transcription"}
    if not required.issubset(set(df_excel.columns)):
        raise ValueError("Excel must contain filename and transcription columns")
    records: List[Dict] = []
    for _, row in df_excel.iterrows():
        record_id = str(uuid.uuid4())
        records.append(
            {
                "id": record_id,
                "filename": str(Path(chunk_folder) / str(row["filename"])),
                "transcription": row["transcription"],
                "correct_transcripts": row.get("correct_transcripts", row["transcription"]),
                "job_id": job_id,
                "locked": False,
                "locked_at": None,
            }
        )
    bulk_import(records)
    return records

