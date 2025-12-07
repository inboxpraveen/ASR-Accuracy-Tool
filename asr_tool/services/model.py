from functools import lru_cache
from typing import Tuple

import torch
from transformers import WhisperForConditionalGeneration, WhisperProcessor


class ModelError(Exception):
    """Raised when model operations fail."""
    pass


@lru_cache(maxsize=1)
def load_model(model_name: str) -> Tuple[WhisperForConditionalGeneration, WhisperProcessor, torch.device]:
    """
    Cached model loader to keep memory footprint predictable.
    Using lru_cache avoids reloading model between tasks.
    """
    if not model_name or not isinstance(model_name, str):
        raise ModelError(f"Invalid model name: {model_name}")
    
    try:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        processor = WhisperProcessor.from_pretrained(model_name)
        model = WhisperForConditionalGeneration.from_pretrained(model_name)
        model.config.forced_decoder_ids = None
        model.eval()
        model.to(device)
        return model, processor, device
    except Exception as e:
        raise ModelError(f"Failed to load model '{model_name}': {str(e)}") from e


def transcribe_file(model, processor, device, wav_path: str) -> str:
    """Transcribe a wav file with Whisper and return plain text."""
    from pathlib import Path
    
    if not wav_path:
        raise ModelError("WAV path cannot be empty")
    
    wav_file = Path(wav_path)
    if not wav_file.exists():
        raise ModelError(f"WAV file does not exist: {wav_path}")
    
    try:
        import torchaudio  # Local import to avoid cost when unused.
        
        waveform, rate = torchaudio.load(wav_path, normalize=True)
        
        if waveform.numel() == 0:
            raise ModelError(f"Empty audio file: {wav_path}")
        
        inputs = processor(
            waveform.squeeze().numpy(),
            sampling_rate=rate,
            return_tensors="pt",
        ).input_features.to(device)
        
        predicted_ids = model.generate(inputs, max_new_tokens=225)
        text = processor.batch_decode(predicted_ids, skip_special_tokens=True)
        
        if isinstance(text, list):
            return text[0] if text else ""
        return text or ""
    except Exception as e:
        raise ModelError(f"Transcription failed for {wav_path}: {str(e)}") from e

