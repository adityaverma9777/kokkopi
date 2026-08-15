"""SSML-LITE — inline prosody/spell markup for agent text output.

Ported from VoiceStudio services/ssml_lite.py.

Allows agents to embed prosody cues directly in generated text:
  * [slow]…[/slow]         — speak slower (speed ≈ 0.85)
  * [fast]…[/fast]         — speak faster (speed ≈ 1.15)
  * [emphasis]…[/emphasis] — mild emphasis: gentle slow-down + emphasis flag
  * [spell]…[/spell]       — spell letter-by-letter

parse_ssml_lite() is called in the streaming pipeline before each sentence
reaches the TTS engine. The engine never sees the raw tags — only the
resolved text with the corresponding speed multiplier applied.
"""
from __future__ import annotations

import re
from typing import Optional

SLOW_SPEED = 0.85
FAST_SPEED = 1.15
EMPHASIS_SPEED = 0.92

_TAGS: dict[str, dict] = {
    "slow": {"speed": SLOW_SPEED, "spell": None, "emphasis": None},
    "fast": {"speed": FAST_SPEED, "spell": None, "emphasis": None},
    "emphasis": {"speed": EMPHASIS_SPEED, "spell": None, "emphasis": True},
    "spell": {"speed": None, "spell": True, "emphasis": None},
}

_TAG_RE = re.compile(
    r"\[(/?)(slow|fast|emphasis|spell)\]",
    re.IGNORECASE,
)


def _resolve(stack: list[str]) -> dict:
    speed: Optional[float] = None
    spell = False
    emphasis = False
    for name in stack:
        spec = _TAGS[name]
        if spec["speed"] is not None:
            speed = spec["speed"]
        if spec["spell"] is not None:
            spell = bool(spec["spell"])
        if spec["emphasis"] is not None:
            emphasis = bool(spec["emphasis"])
    return {"speed": speed, "spell": spell, "emphasis": emphasis}


def parse_ssml_lite(text: str) -> list[dict]:
    """Split one line of SSML-LITE markup into ordered prosody segments.

    Returns [{"text": str, "speed": float|None, "spell": bool, "emphasis": bool}, ...]
    """
    if not text:
        return []
    if "[" not in text:
        return [{"text": text, "speed": None, "spell": False, "emphasis": False}]

    segments: list[dict] = []
    stack: list[str] = []
    last = 0

    def emit(chunk: str) -> None:
        if not chunk:
            return
        props = _resolve(stack)
        seg = {"text": chunk, **props}
        if segments:
            prev = segments[-1]
            if prev["speed"] == seg["speed"] and prev["spell"] == seg["spell"] and prev["emphasis"] == seg["emphasis"]:
                prev["text"] += chunk
                return
        segments.append(seg)

    for m in _TAG_RE.finditer(text):
        emit(text[last:m.start()])
        last = m.end()
        is_close = m.group(1) == "/"
        name = m.group(2).lower()
        if is_close:
            for i in range(len(stack) - 1, -1, -1):
                if stack[i] == name:
                    del stack[i]
                    break
        else:
            stack.append(name)

    emit(text[last:])

    if not segments:
        return []
    return segments


def strip_ssml_lite(text: str) -> str:
    """Remove all SSML-LITE tags, returning plain text."""
    if not text or "[" not in text:
        return text or ""
    return _TAG_RE.sub("", text)


def spell_out(word: str) -> str:
    """Space out a word for the [spell] case: 'USA' → 'U S A'."""
    if not word:
        return ""
    compact = "".join(word.split())
    return " ".join(compact)


def apply_ssml_lite_to_text(text: str) -> str:
    """Resolve SSML-LITE to plain text, expanding [spell] spans.

    Strips prosody tags (speed/emphasis are applied at TTS level)
    and expands [spell] spans into space-separated letters.
    """
    segments = parse_ssml_lite(text)
    parts = []
    for seg in segments:
        t = seg["text"]
        if seg.get("spell"):
            t = spell_out(t)
        parts.append(t)
    return "".join(parts)
