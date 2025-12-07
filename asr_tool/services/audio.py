import os
import subprocess
from pathlib import Path
from typing import Iterable, List

from asr_tool.config import SEGMENTS_DIR


AUDIO_EXTENSIONS = (".mp3", ".wav", ".wma", ".mpeg", ".opus", ".flac", ".m4a")


class AudioProcessingError(Exception):
    """Raised when audio processing fails."""
    pass


def iter_audio_files(folder_path: str) -> Iterable[Path]:
    """Yield audio files under a folder, skipping everything else."""
    try:
        root = Path(folder_path).expanduser().resolve()
        if not root.exists():
            raise AudioProcessingError(f"Folder does not exist: {folder_path}")
        if not root.is_dir():
            raise AudioProcessingError(f"Path is not a directory: {folder_path}")
        
        for base, _, files in os.walk(root):
            for file in files:
                if file.lower().endswith(AUDIO_EXTENSIONS):
                    yield Path(base) / file
    except PermissionError as e:
        raise AudioProcessingError(f"Permission denied accessing folder: {folder_path}") from e
    except Exception as e:
        raise AudioProcessingError(f"Error reading folder: {str(e)}") from e


def convert_to_wav(source_path: Path, job_id: str | None = None) -> Path:
    """Convert any audio to 16k mono wav efficiently via ffmpeg."""
    if not source_path.exists():
        raise AudioProcessingError(f"Source file does not exist: {source_path}")
    
    try:
        target_dir = SEGMENTS_DIR / (job_id or "")
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / f"{source_path.stem}.wav"
        
        command = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(source_path),
            "-ac",
            "1",
            "-ar",
            "16000",
            "-acodec",
            "pcm_s16le",
            str(target),
            "-y",
        ]
        
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        
        if not target.exists():
            raise AudioProcessingError(f"FFmpeg failed to create output file: {target}")
        
        return target
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr if e.stderr else str(e)
        raise AudioProcessingError(f"FFmpeg conversion failed: {error_msg}") from e
    except Exception as e:
        raise AudioProcessingError(f"Audio conversion error: {str(e)}") from e


def segment_audio(wav_path: Path, job_id: str | None = None, segment_seconds: int = 30) -> List[Path]:
    """
    Split a wav file into fixed windows using ffmpeg's streaming segmenter.
    This avoids loading large files into memory and keeps files manageable.
    """
    if not wav_path.exists():
        raise AudioProcessingError(f"WAV file does not exist: {wav_path}")
    
    if segment_seconds <= 0:
        raise AudioProcessingError(f"Invalid segment duration: {segment_seconds}")
    
    try:
        base_dir = SEGMENTS_DIR / (job_id or "")
        target_dir = base_dir / wav_path.stem
        target_dir.mkdir(parents=True, exist_ok=True)
        pattern = target_dir / "%03d.wav"
        
        command = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(wav_path),
            "-f",
            "segment",
            "-segment_time",
            str(segment_seconds),
            "-c",
            "copy",
            str(pattern),
            "-y",
        ]
        
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        segments = sorted(target_dir.glob("*.wav"))
        
        if not segments:
            raise AudioProcessingError(f"No segments created from {wav_path}")
        
        return segments
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr if e.stderr else str(e)
        raise AudioProcessingError(f"FFmpeg segmentation failed: {error_msg}") from e
    except Exception as e:
        raise AudioProcessingError(f"Audio segmentation error: {str(e)}") from e

