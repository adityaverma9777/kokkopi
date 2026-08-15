"""Speech rate utilities — duration estimation and SSML speed enforcement.

Provides language-aware duration estimation and applies speed multipliers
from SSML-LITE parse results to TTS synthesis parameters.

Duration constants derived from Pellegrino et al. 2011
(Cross-language information rate) and calibration against TTS engine outputs.
"""
from __future__ import annotations

from typing import Optional

_RATE_CPS: dict[str, float] = {
    "en": 15.0, "de": 14.0, "fr": 15.0, "es": 15.5, "it": 15.0, "pt": 15.0,
    "ja": 10.0, "ko": 10.0, "zh": 6.0,
    "hi": 17.0, "bn": 17.0, "ta": 14.0, "te": 14.0, "mr": 16.0,
    "gu": 16.0, "kn": 14.0, "ml": 14.0, "pa": 16.0, "or": 16.0, "ur": 13.0,
    "ar": 12.0, "he": 12.0, "fa": 13.0,
    "th": 10.0, "vi": 16.0, "id": 14.0, "ms": 14.0,
    "ru": 13.0, "pl": 13.0, "uk": 13.0, "cs": 13.0, "tr": 12.0,
    "el": 14.0, "nl": 14.0, "sv": 14.0, "no": 14.0, "da": 14.0, "fi": 13.0,
}


def expected_duration(text: str, lang: str = "en") -> float:
    """Rough CPS-based spoken duration estimate. Returns seconds."""
    cps = _RATE_CPS.get(lang.split("-")[0].lower(), 13.0)
    return len(text) / max(1.0, cps)


def apply_speed_to_segments(segments: list[dict], base_speed: float = 1.0) -> list[dict]:
    """Multiply each segment's speed by base_speed.

    Segments come from parse_ssml_lite(). If a segment has no speed override
    (speed=None), the base_speed is used as-is (engine default for base=1.0,
    otherwise the caller's rate multiplier).

    Returns a new list with speed values filled in.
    """
    result = []
    for seg in segments:
        effective_speed: Optional[float] = seg.get("speed")
        if effective_speed is None:
            effective_speed = base_speed if base_speed != 1.0 else None
        else:
            effective_speed = effective_speed * base_speed
        result.append({**seg, "speed": effective_speed})
    return result


def clamp_speed(speed: Optional[float], lo: float = 0.5, hi: float = 2.0) -> Optional[float]:
    """Clamp a speed multiplier to a safe range. None passes through."""
    if speed is None:
        return None
    return max(lo, min(hi, speed))
