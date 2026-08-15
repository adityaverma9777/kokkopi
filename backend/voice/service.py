"""Kokkopi Voice Service — Kokoro TTS + faster-whisper ASR.

Single entry point for all voice operations. Replaces the previous
VoiceStudio bridge which required the VoiceStudio repo on the Python path.

TTS Engine: Kokoro-82M (MIT license, hexgrad/Kokoro-82M on HF Hub)
  - 21 voices across 9 languages
  - Runs on CPU and GPU
  - No API keys required
  - Auto-downloaded on first use via HuggingFace Hub

ASR Engine: faster-whisper (small model by default)
  - Multilingual transcription
  - Returns detected language code
  - Thread-safe lazy load
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, AsyncGenerator, Optional

from voice.adapters.kokoro_tts import (
    synthesize as kokoro_synthesize,
    VOICE_CATALOG,
    _is_kokoro_available,
    KOKORO_SAMPLE_RATE,
)
from voice.adapters.lang_detect import (
    whisper_lang_to_kokoro,
    detect_language_from_text,
    resolve_voice_for_session,
)
from voice.pipeline.asr import transcribe as _asr_transcribe, is_available as asr_is_available
from voice.pipeline.chunked_tts import split_text_into_chunks, concatenate_audio_chunks

logger = logging.getLogger("kokkopi.voice_service")


class KokkopiVoiceService:
    """Core voice service: TTS synthesis, ASR transcription, voice gallery."""

    async def synthesize(
        self,
        text: str,
        voice_id: str = "af_heart",
        *,
        speed: float = 1.0,
        language: Optional[str] = None,
    ) -> bytes:
        """Synthesize text → WAV bytes. Long texts are chunked automatically."""
        chunks = split_text_into_chunks(text)
        if len(chunks) == 1:
            return await kokoro_synthesize(chunks[0], voice_id, speed=speed, language=language)

        import io
        import numpy as np
        try:
            import soundfile as sf
        except ImportError:
            logger.warning("soundfile not installed — falling back to single-shot synthesis")
            return await kokoro_synthesize(text, voice_id, speed=speed, language=language)

        audio_parts = []
        for chunk in chunks:
            wav_bytes = await kokoro_synthesize(chunk, voice_id, speed=speed, language=language)
            if wav_bytes:
                buf = io.BytesIO(wav_bytes)
                audio, _ = sf.read(buf, dtype="float32")
                audio_parts.append(audio)

        if not audio_parts:
            return b""

        import numpy as np
        combined = np.concatenate(audio_parts)
        out_buf = io.BytesIO()
        sf.write(out_buf, combined, KOKORO_SAMPLE_RATE, format="WAV", subtype="PCM_16")
        return out_buf.getvalue()

    async def synthesize_for_session(
        self,
        text: str,
        *,
        agent_voice_id: Optional[str] = None,
        detected_language: Optional[str] = None,
        speed: float = 1.0,
    ) -> bytes:
        """Synthesize with automatic multilingual voice selection.

        Detects the language of the text if not provided, then selects the
        best matching voice from the Kokoro gallery. If the agent owner has
        a configured voice that speaks the detected language, it is preferred.
        """
        if not detected_language:
            detected_language = detect_language_from_text(text)

        voice_id = resolve_voice_for_session(
            detected_language,
            agent_voice_id=agent_voice_id,
        )
        return await self.synthesize(text, voice_id, speed=speed, language=detected_language)

    async def transcribe(self, audio_bytes: bytes) -> dict:
        """Transcribe audio → {"text": str, "language": str (Kokoro lang_code)}.

        The detected language is returned in Kokoro format so it can be passed
        directly to synthesize_for_session().
        """
        try:
            from voice.pipeline.asr import transcribe_with_language
            text, whisper_lang = await transcribe_with_language(audio_bytes)
            lang_code = whisper_lang_to_kokoro(whisper_lang or "en")
            return {"text": text, "language": lang_code, "whisper_language": whisper_lang}
        except ImportError:
            text = await _asr_transcribe(audio_bytes)
            return {"text": text, "language": "en-us", "whisper_language": "en"}
        except Exception as e:
            logger.error("Transcription failed: %s", e)
            return {"text": "", "language": "en-us", "whisper_language": "en"}

    async def list_voices(self) -> list[dict]:
        return VOICE_CATALOG

    async def health(self) -> dict:
        kokoro_ok, kokoro_msg = _is_kokoro_available()
        asr_ok, asr_msg = asr_is_available()
        return {
            "status": "ok" if kokoro_ok else "degraded",
            "tts": {"engine": "kokoro-82m", "available": kokoro_ok, "message": kokoro_msg, "voices": len(VOICE_CATALOG)},
            "asr": {"engine": "faster-whisper", "available": asr_ok, "message": asr_msg},
        }


voice_service = KokkopiVoiceService()
