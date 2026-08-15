"""Kokoro TTS adapter — multilingual, high-quality, zero-dependency TTS.

Kokoro is an 82M parameter TTS model (MIT license) supporting 8+ languages.
It runs efficiently on both CPU and GPU with no API keys required.

Supported languages:
  en-us  English (US) — af_heart, af_bella, af_nova, am_adam, am_michael
  en-gb  English (UK) — bf_emma, bf_isabella, bm_george, bm_lewis
  es-es  Spanish       — ef_dora, em_alex, em_santa
  fr-fr  French        — ff_siwis
  ja     Japanese      — jf_alpha, jf_gongitsune, jm_kumo
  zh-cn  Chinese       — zf_xiaobei, zf_xiaoni, zf_xiaoyi, zm_yunjian
  ko     Korean        — kf_luna, km_yunho
  pt-br  Portuguese    — pf_dora, pm_alex
  hi     Hindi         — hf_alpha, hm_omega

Model: hexgrad/Kokoro-82M on HF Hub (auto-downloaded on first use)
"""
from __future__ import annotations

import asyncio
import io
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from pathlib import Path
from typing import Optional

logger = logging.getLogger("kokkopi.kokoro_tts")

_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="kokkopi_tts")
_kokoro_pipeline = None
_kokoro_lock = asyncio.Lock() if asyncio.get_event_loop_policy() else None

KOKORO_SAMPLE_RATE = 24000
KOKORO_MODEL_ID = os.environ.get("KOKORO_MODEL_ID", "hexgrad/Kokoro-82M")


VOICE_CATALOG: list[dict] = [
    {
        "id": "af_heart",
        "name": "Heart",
        "description": "Warm, expressive American female. Perfect for friendly customer support.",
        "gender": "female",
        "lang_code": "en-us",
        "language": "English",
        "language_flag": "🇺🇸",
        "tags": ["warm", "friendly", "expressive"],
    },
    {
        "id": "af_bella",
        "name": "Bella",
        "description": "Clear, professional American female. Ideal for business and retail.",
        "gender": "female",
        "lang_code": "en-us",
        "language": "English",
        "language_flag": "🇺🇸",
        "tags": ["professional", "clear", "polished"],
    },
    {
        "id": "af_nova",
        "name": "Nova",
        "description": "Energetic, modern American female. Great for tech and startups.",
        "gender": "female",
        "lang_code": "en-us",
        "language": "English",
        "language_flag": "🇺🇸",
        "tags": ["energetic", "modern", "upbeat"],
    },
    {
        "id": "am_adam",
        "name": "Adam",
        "description": "Deep, authoritative American male. Ideal for finance and legal.",
        "gender": "male",
        "lang_code": "en-us",
        "language": "English",
        "language_flag": "🇺🇸",
        "tags": ["deep", "authoritative", "confident"],
    },
    {
        "id": "am_michael",
        "name": "Michael",
        "description": "Neutral, trustworthy American male. Works for any industry.",
        "gender": "male",
        "lang_code": "en-us",
        "language": "English",
        "language_flag": "🇺🇸",
        "tags": ["neutral", "trustworthy", "versatile"],
    },
    {
        "id": "bf_emma",
        "name": "Emma",
        "description": "Sophisticated British female. Ideal for luxury and premium brands.",
        "gender": "female",
        "lang_code": "en-gb",
        "language": "English (UK)",
        "language_flag": "🇬🇧",
        "tags": ["sophisticated", "british", "premium"],
    },
    {
        "id": "bf_isabella",
        "name": "Isabella",
        "description": "Articulate, warm British female. Perfect for education and healthcare.",
        "gender": "female",
        "lang_code": "en-gb",
        "language": "English (UK)",
        "language_flag": "🇬🇧",
        "tags": ["articulate", "warm", "professional"],
    },
    {
        "id": "bm_george",
        "name": "George",
        "description": "Distinguished British male. Great for finance and consulting.",
        "gender": "male",
        "lang_code": "en-gb",
        "language": "English (UK)",
        "language_flag": "🇬🇧",
        "tags": ["distinguished", "british", "authoritative"],
    },
    {
        "id": "bm_lewis",
        "name": "Lewis",
        "description": "Friendly, conversational British male. Works for any casual business.",
        "gender": "male",
        "lang_code": "en-gb",
        "language": "English (UK)",
        "language_flag": "🇬🇧",
        "tags": ["friendly", "conversational", "british"],
    },
    {
        "id": "ef_dora",
        "name": "Dora",
        "description": "Natural, expressive Spanish female.",
        "gender": "female",
        "lang_code": "es-es",
        "language": "Español",
        "language_flag": "🇪🇸",
        "tags": ["natural", "expressive", "spanish"],
    },
    {
        "id": "em_alex",
        "name": "Alex (ES)",
        "description": "Confident Spanish male voice.",
        "gender": "male",
        "lang_code": "es-es",
        "language": "Español",
        "language_flag": "🇪🇸",
        "tags": ["confident", "spanish"],
    },
    {
        "id": "ff_siwis",
        "name": "Siwis",
        "description": "Elegant French female voice.",
        "gender": "female",
        "lang_code": "fr-fr",
        "language": "Français",
        "language_flag": "🇫🇷",
        "tags": ["elegant", "french"],
    },
    {
        "id": "jf_alpha",
        "name": "Alpha",
        "description": "Natural Japanese female voice.",
        "gender": "female",
        "lang_code": "ja",
        "language": "日本語",
        "language_flag": "🇯🇵",
        "tags": ["natural", "japanese"],
    },
    {
        "id": "jm_kumo",
        "name": "Kumo",
        "description": "Calm Japanese male voice.",
        "gender": "male",
        "lang_code": "ja",
        "language": "日本語",
        "language_flag": "🇯🇵",
        "tags": ["calm", "japanese"],
    },
    {
        "id": "zf_xiaobei",
        "name": "Xiaobei",
        "description": "Clear, modern Chinese female voice.",
        "gender": "female",
        "lang_code": "zh-cn",
        "language": "中文",
        "language_flag": "🇨🇳",
        "tags": ["clear", "modern", "chinese"],
    },
    {
        "id": "zm_yunjian",
        "name": "Yunjian",
        "description": "Professional Chinese male voice.",
        "gender": "male",
        "lang_code": "zh-cn",
        "language": "中文",
        "language_flag": "🇨🇳",
        "tags": ["professional", "chinese"],
    },
    {
        "id": "kf_luna",
        "name": "Luna",
        "description": "Bright Korean female voice.",
        "gender": "female",
        "lang_code": "ko",
        "language": "한국어",
        "language_flag": "🇰🇷",
        "tags": ["bright", "korean"],
    },
    {
        "id": "km_yunho",
        "name": "Yunho",
        "description": "Clear Korean male voice.",
        "gender": "male",
        "lang_code": "ko",
        "language": "한국어",
        "language_flag": "🇰🇷",
        "tags": ["clear", "korean"],
    },
    {
        "id": "pf_dora",
        "name": "Dora (PT)",
        "description": "Warm Brazilian Portuguese female voice.",
        "gender": "female",
        "lang_code": "pt-br",
        "language": "Português",
        "language_flag": "🇧🇷",
        "tags": ["warm", "portuguese"],
    },
    {
        "id": "hf_alpha",
        "name": "Priya",
        "description": "Natural Indian Hindi female voice.",
        "gender": "female",
        "lang_code": "hi",
        "language": "हिंदी",
        "language_flag": "🇮🇳",
        "tags": ["natural", "hindi", "indian"],
    },
    {
        "id": "hm_omega",
        "name": "Arjun",
        "description": "Clear Indian Hindi male voice.",
        "gender": "male",
        "lang_code": "hi",
        "language": "हिंदी",
        "language_flag": "🇮🇳",
        "tags": ["clear", "hindi", "indian"],
    },
]

_VOICE_INDEX = {v["id"]: v for v in VOICE_CATALOG}

SUPPORTED_LANGUAGES = sorted({v["lang_code"] for v in VOICE_CATALOG})

DEFAULT_VOICE_BY_LANG: dict[str, str] = {
    "en-us": "af_heart",
    "en-gb": "bf_emma",
    "en": "af_heart",
    "es-es": "ef_dora",
    "es": "ef_dora",
    "fr-fr": "ff_siwis",
    "fr": "ff_siwis",
    "ja": "jf_alpha",
    "zh-cn": "zf_xiaobei",
    "zh": "zf_xiaobei",
    "ko": "kf_luna",
    "pt-br": "pf_dora",
    "pt": "pf_dora",
    "hi": "hf_alpha",
}


def _is_kokoro_available() -> tuple[bool, str]:
    try:
        import kokoro
        return True, "kokoro installed"
    except ImportError:
        return False, "kokoro not installed — run: pip install kokoro soundfile"


def _load_pipeline_sync(voice_id: str = "af_heart"):
    """Load the Kokoro pipeline (blocking). Called from thread pool."""
    from kokoro import KPipeline
    lang_code = _VOICE_INDEX.get(voice_id, {}).get("lang_code", "en-us")
    pipeline = KPipeline(lang_code=lang_code, repo_id=KOKORO_MODEL_ID)
    return pipeline


def _synthesize_sync(text: str, voice_id: str, speed: float = 1.0) -> bytes:
    """Synthesize audio synchronously using Kokoro. Returns WAV bytes."""
    import soundfile as sf
    import numpy as np
    from kokoro import KPipeline

    lang_code = _VOICE_INDEX.get(voice_id, {}).get("lang_code", "en-us")
    pipeline = KPipeline(lang_code=lang_code, repo_id=KOKORO_MODEL_ID)

    audio_parts = []
    for _, _, audio in pipeline(text, voice=voice_id, speed=speed, split_pattern=r"\n+"):
        if audio is not None and len(audio) > 0:
            audio_parts.append(audio)

    if not audio_parts:
        return b""

    combined = np.concatenate(audio_parts)
    buf = io.BytesIO()
    sf.write(buf, combined, KOKORO_SAMPLE_RATE, format="WAV", subtype="PCM_16")
    return buf.getvalue()


async def synthesize(
    text: str,
    voice_id: str = "af_heart",
    *,
    speed: float = 1.0,
    language: Optional[str] = None,
) -> bytes:
    """Synthesize text to WAV bytes using Kokoro TTS.

    If language is provided and no voice_id matches it, auto-selects the
    default voice for that language.

    Args:
        text: Text to synthesize (after normalization/pronunciation pass).
        voice_id: Kokoro voice identifier (e.g. 'af_heart').
        speed: Speaking rate multiplier (0.5–2.0, default 1.0).
        language: ISO language code hint (used for auto-selection if needed).

    Returns:
        WAV audio bytes, or empty bytes if synthesis fails.
    """
    ok, msg = _is_kokoro_available()
    if not ok:
        logger.warning("Kokoro not available: %s", msg)
        return b""

    if voice_id not in _VOICE_INDEX:
        lang = language or "en"
        voice_id = DEFAULT_VOICE_BY_LANG.get(lang, DEFAULT_VOICE_BY_LANG.get(lang.split("-")[0], "af_heart"))
        logger.info("Unknown voice_id; auto-selected %s for lang=%s", voice_id, lang)

    speed = max(0.5, min(2.0, speed))

    loop = asyncio.get_event_loop()
    try:
        return await loop.run_in_executor(_executor, _synthesize_sync, text, voice_id, speed)
    except Exception as e:
        logger.error("Kokoro synthesis failed: %s", e)
        return b""


def get_voice(voice_id: str) -> Optional[dict]:
    return _VOICE_INDEX.get(voice_id)


def voices_for_language(lang_code: str) -> list[dict]:
    lang = lang_code.lower()
    return [v for v in VOICE_CATALOG if v["lang_code"] == lang or v["lang_code"].split("-")[0] == lang.split("-")[0]]


def auto_select_voice(language: str, *, prefer_gender: Optional[str] = None) -> str:
    """Choose the best voice for a given detected language.

    Falls back to the English default if no voice exists for the language.
    Optionally biases toward a preferred gender.
    """
    lang = language.lower().split("-")[0]
    candidates = voices_for_language(language) or voices_for_language(lang)
    if not candidates:
        return "af_heart"
    if prefer_gender:
        gendered = [v for v in candidates if v.get("gender") == prefer_gender]
        if gendered:
            candidates = gendered
    lang_key = language.lower()
    default = DEFAULT_VOICE_BY_LANG.get(lang_key) or DEFAULT_VOICE_BY_LANG.get(lang, candidates[0]["id"])
    for c in candidates:
        if c["id"] == default:
            return default
    return candidates[0]["id"]
