"""Language detection for incoming visitor messages.

Uses faster-whisper's built-in language detection from audio (most accurate),
or langdetect as a fallback for text-only inputs.

For voice agents: language comes from ASR output (faster-whisper detects it
automatically during transcription). For text-only chat: we detect from text.

Supported languages map to Kokoro TTS voices automatically.
"""
from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger("kokkopi.lang_detect")

_WHISPER_TO_KOKORO_LANG: dict[str, str] = {
    "en": "en-us",
    "es": "es-es",
    "fr": "fr-fr",
    "ja": "ja",
    "zh": "zh-cn",
    "ko": "ko",
    "pt": "pt-br",
    "hi": "hi",
    "de": "en-us",
    "it": "en-us",
    "ru": "en-us",
    "ar": "en-us",
}

_DEFAULT_LANG = "en-us"


def whisper_lang_to_kokoro(whisper_lang: str) -> str:
    """Convert a faster-whisper language code to a Kokoro lang_code."""
    lang = (whisper_lang or "en").lower().split("-")[0]
    return _WHISPER_TO_KOKORO_LANG.get(lang, _DEFAULT_LANG)


def detect_language_from_text(text: str) -> str:
    """Detect language from plain text using langdetect.

    Returns a Kokoro lang_code. Falls back to 'en-us' on any error.
    This is used for text-only chat sessions where no ASR output is available.
    """
    if not text or not text.strip():
        return _DEFAULT_LANG
    try:
        from langdetect import detect as _detect
        lang = _detect(text)
        return whisper_lang_to_kokoro(lang)
    except Exception:
        try:
            if any(ord(c) > 0x3000 for c in text):
                if any('\u3040' <= c <= '\u30FF' for c in text):
                    return "ja"
                if any('\uAC00' <= c <= '\uD7AF' for c in text):
                    return "ko"
                if any('\u4E00' <= c <= '\u9FFF' for c in text):
                    return "zh-cn"
        except Exception:
            pass
        return _DEFAULT_LANG


def is_supported_language(lang_code: str) -> bool:
    """Check if the Kokoro adapter has voices for this language."""
    from voice.adapters.kokoro_tts import SUPPORTED_LANGUAGES
    return lang_code in SUPPORTED_LANGUAGES


def resolve_voice_for_session(
    detected_lang: str,
    *,
    agent_voice_id: Optional[str] = None,
    prefer_gender: Optional[str] = None,
) -> str:
    """Resolve the final voice ID for a response.

    Priority:
      1. If the agent has a configured voice AND it speaks the detected language → use it.
      2. If the agent voice speaks a different language → auto-select for detected lang.
      3. Fall back to English default.

    Args:
        detected_lang: Kokoro lang_code from ASR or text detection.
        agent_voice_id: The voice the agent owner configured.
        prefer_gender: Optional gender bias for auto-selection.

    Returns:
        A valid Kokoro voice_id.
    """
    from voice.adapters.kokoro_tts import get_voice, auto_select_voice

    if agent_voice_id:
        voice_meta = get_voice(agent_voice_id)
        if voice_meta:
            voice_lang = voice_meta.get("lang_code", "en-us")
            if voice_lang == detected_lang or voice_lang.split("-")[0] == detected_lang.split("-")[0]:
                return agent_voice_id

    return auto_select_voice(detected_lang, prefer_gender=prefer_gender)
