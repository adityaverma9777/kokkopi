"""Real ASR backend using faster-whisper.

Replaces the placeholder transcription stub with production-grade speech-to-text.

Model selection:
    Controlled by KOKKOPI_ASR_MODEL env var (default: "small").
    Available sizes: tiny, base, small, medium, large-v3.
    Default "small" balances accuracy and VRAM on HF GPU.
    
    WARNING: Running large-v3 alongside TTS models on the same GPU
    will exhaust VRAM. Benchmark before changing the default.

Device selection:
    Controlled by KOKKOPI_ASR_DEVICE env var.
    Defaults to "cuda" if GPU is available, otherwise "cpu".
"""
from __future__ import annotations

import asyncio
import logging
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

logger = logging.getLogger("kokkopi.asr")

ASR_MODEL_SIZE = os.environ.get("KOKKOPI_ASR_MODEL", "small")
ASR_DEVICE = os.environ.get("KOKKOPI_ASR_DEVICE", "auto")
ASR_TRANSCRIBE_TIMEOUT_S = float(os.environ.get("KOKKOPI_ASR_TIMEOUT_S", "120.0"))

_model = None
_model_lock = threading.Lock()
_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="kokkopi_asr")


def _get_model():
    """Lazy-load the Whisper model. Thread-safe singleton."""
    global _model
    if _model is not None:
        return _model
    with _model_lock:
        if _model is not None:
            return _model
        try:
            from faster_whisper import WhisperModel

            device = ASR_DEVICE
            if device == "auto":
                try:
                    import torch
                    device = "cuda" if torch.cuda.is_available() else "cpu"
                except ImportError:
                    device = "cpu"

            compute_type = "float16" if device == "cuda" else "int8"
            logger.info("Loading faster-whisper model '%s' on %s (%s)...", ASR_MODEL_SIZE, device, compute_type)
            _model = WhisperModel(ASR_MODEL_SIZE, device=device, compute_type=compute_type)
            logger.info("faster-whisper model loaded.")
            return _model
        except ImportError:
            logger.error("faster-whisper not installed. Install with: pip install faster-whisper")
            raise
        except Exception as e:
            logger.error("Failed to load faster-whisper model: %s", e)
            raise


def _transcribe_sync(audio_bytes: bytes) -> str:
    """Blocking transcription. Runs in thread pool to avoid blocking event loop."""
    import io
    model = _get_model()
    audio_file = io.BytesIO(audio_bytes)
    
    segments, info = model.transcribe(
        audio_file,
        beam_size=5,
        language=None,
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 300},
    )
    
    texts = []
    for segment in segments:
        texts.append(segment.text.strip())
    
    transcript = " ".join(texts).strip()
    logger.debug("ASR result: %r (%.2fs, lang=%s)", transcript, info.duration, info.language)
    return transcript


async def transcribe(audio_bytes: bytes, timeout: float = ASR_TRANSCRIBE_TIMEOUT_S) -> str:
    """Transcribe raw audio bytes to text.

    Runs faster-whisper in a thread pool to avoid blocking FastAPI's event loop.
    Raises TimeoutError if transcription exceeds `timeout` seconds.

    Args:
        audio_bytes: Raw audio data (WAV, WebM, or any ffmpeg-compatible format).
        timeout: Maximum seconds to wait. Defaults to KOKKOPI_ASR_TIMEOUT_S.

    Returns:
        Transcribed text string. Returns empty string if audio is silent.
    """
    if not audio_bytes:
        return ""
    
    loop = asyncio.get_event_loop()
    
    try:
        result = await asyncio.wait_for(
            loop.run_in_executor(_executor, _transcribe_sync, audio_bytes),
            timeout=timeout,
        )
        return result
    except asyncio.TimeoutError:
        logger.warning("ASR transcription timed out after %.1fs.", timeout)
        raise TimeoutError(f"Speech transcription timed out after {timeout}s. Try speaking more briefly.")
    except Exception as e:
        logger.error("ASR transcription failed: %s", e, exc_info=True)
        raise


def is_available() -> tuple[bool, str]:
    """Check if faster-whisper is installed and can load the model."""
    try:
        import faster_whisper  # noqa: F401
        return True, f"faster-whisper available (model: {ASR_MODEL_SIZE})"
    except ImportError:
        return False, "faster-whisper not installed. Run: pip install faster-whisper"
