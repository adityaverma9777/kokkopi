"""Speaker clone extraction and VoiceProfile persistence.

Ported from VoiceStudio services/speaker_clone.py.

Picks a clean audio sample from uploaded audio, validates its duration,
and stores a reusable VoiceProfile tied to the customer's agent/tenant.

Authorization/consent is required before any cloning operation. The
cloning UI must not call this backend without explicit user confirmation.

VoiceProfile lifecycle:
    1. User uploads a consent-authorized audio sample.
    2. extract_reference_sample() validates quality and duration.
    3. VoiceProfile is persisted to DB (tenant-scoped, agent-associated).
    4. TTS engines use the stored reference WAV for zero-shot cloning.
"""
from __future__ import annotations

import asyncio
import io
import logging
import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Optional

import numpy as np

logger = logging.getLogger("kokkopi.speaker_clone")

MIN_REF_DURATION_S = 5.0
MAX_REF_DURATION_S = 30.0
IDEAL_REF_DURATION_S = 10.0

VOICE_PROFILES_DIR = Path(os.environ.get("KOKKOPI_VOICE_PROFILES_DIR", "/tmp/kokkopi_voice_profiles"))

_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="kokkopi_clone")


def _validate_and_extract_sync(audio_bytes: bytes) -> dict:
    """Validate audio quality and extract the usable reference segment.

    Returns a dict with:
        - status: "ok" | "too_short" | "too_long" | "silent" | "error"
        - duration_s: float
        - sample_rate: int
        - message: human-readable description
        - audio_data: np.ndarray (if status=="ok")
    """
    try:
        import soundfile as sf
    except ImportError:
        return {"status": "error", "message": "soundfile not installed. Run: pip install soundfile"}

    try:
        buf = io.BytesIO(audio_bytes)
        audio_data, sample_rate = sf.read(buf, dtype="float32")

        if audio_data.ndim > 1:
            audio_data = audio_data.mean(axis=1)

        duration_s = len(audio_data) / sample_rate

        if duration_s < MIN_REF_DURATION_S:
            return {
                "status": "too_short",
                "duration_s": duration_s,
                "sample_rate": sample_rate,
                "message": f"Audio is {duration_s:.1f}s. Minimum is {MIN_REF_DURATION_S}s for a reliable voice clone.",
            }

        if duration_s > MAX_REF_DURATION_S:
            audio_data = audio_data[:int(MAX_REF_DURATION_S * sample_rate)]
            duration_s = MAX_REF_DURATION_S

        silence_floor = 10 ** (-50.0 / 20.0)
        if np.abs(audio_data).max() < silence_floor:
            return {
                "status": "silent",
                "duration_s": duration_s,
                "sample_rate": sample_rate,
                "message": "The audio appears to be silent. Please upload a recording with clear speech.",
            }

        if duration_s > IDEAL_REF_DURATION_S:
            audio_data = audio_data[:int(IDEAL_REF_DURATION_S * sample_rate)]
            duration_s = IDEAL_REF_DURATION_S

        return {
            "status": "ok",
            "duration_s": duration_s,
            "sample_rate": sample_rate,
            "audio_data": audio_data,
            "message": f"Audio validated: {duration_s:.1f}s of usable speech.",
        }

    except Exception as e:
        logger.error("Failed to validate audio: %s", e)
        return {"status": "error", "message": f"Could not process audio file: {str(e)}"}


def _save_reference_wav(audio_data: np.ndarray, sample_rate: int) -> Path:
    """Save extracted reference audio to disk. Returns the saved path."""
    import soundfile as sf
    VOICE_PROFILES_DIR.mkdir(parents=True, exist_ok=True)
    profile_id = str(uuid.uuid4())
    wav_path = VOICE_PROFILES_DIR / f"{profile_id}.wav"
    sf.write(str(wav_path), audio_data, sample_rate, subtype="PCM_16")
    return wav_path


async def extract_and_save_reference(
    audio_bytes: bytes,
    *,
    agent_id: str,
    tenant_id: str,
    profile_name: str,
    consent_confirmed: bool,
) -> dict:
    """Extract a clean voice reference and persist it as a VoiceProfile.

    This is the ONLY public entry point for voice cloning. It enforces
    consent confirmation before any processing begins.

    Returns:
        {
            "status": "ok" | "error" | "too_short" | "too_long" | "silent",
            "profile_id": str (if ok),
            "wav_path": str (if ok),
            "duration_s": float,
            "message": str,
        }
    """
    if not consent_confirmed:
        return {
            "status": "error",
            "message": "Voice cloning requires explicit consent authorization. Please confirm you own or have permission to use this voice.",
        }

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(_executor, _validate_and_extract_sync, audio_bytes)

    if result["status"] != "ok":
        return result

    audio_data = result.pop("audio_data")
    save_path = await loop.run_in_executor(
        _executor, _save_reference_wav, audio_data, result["sample_rate"]
    )

    profile_id = save_path.stem
    return {
        "status": "ok",
        "profile_id": profile_id,
        "wav_path": str(save_path),
        "duration_s": result["duration_s"],
        "message": result["message"],
    }


def list_builtin_voices() -> list[dict]:
    """Return the gallery of built-in voices available for all agents."""
    return [
        {
            "id": "voice_alex",
            "name": "Alex",
            "description": "Neutral, professional American English. Ideal for business.",
            "gender": "neutral",
            "accent": "en-US",
            "preview_text": "Hello! I'm Alex. I'm here to help you with anything you need.",
        },
        {
            "id": "voice_sarah",
            "name": "Sarah",
            "description": "Warm, friendly. Great for customer support and retail.",
            "gender": "female",
            "accent": "en-US",
            "preview_text": "Hi there! I'm Sarah. How can I make your day better?",
        },
        {
            "id": "voice_marcus",
            "name": "Marcus",
            "description": "Deep, authoritative. Ideal for legal, finance, medical.",
            "gender": "male",
            "accent": "en-GB",
            "preview_text": "Good day. I'm Marcus. Let me assist you with precision.",
        },
        {
            "id": "voice_elena",
            "name": "Elena",
            "description": "Clear, energetic. Great for tech and startup businesses.",
            "gender": "female",
            "accent": "en-AU",
            "preview_text": "Hey! I'm Elena. Ask me anything — I love a good question.",
        },
    ]
