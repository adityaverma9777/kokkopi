"""Pronunciation lexicon — per-agent word respelling before TTS.

Ported from VoiceStudio services/pronunciation.py.

Maps a word (or short phrase) to a respelling the TTS engine pronounces
correctly. Example: {"Kokkopi": "Koh-koh-pee", "GIF": "jiff"}.

Applied at the agent level, so each agent can have custom pronunciations
for its business's brand names, products, and local terms.
"""
from __future__ import annotations

import re
from typing import Optional


def normalize_lexicon(lexicon: Optional[dict]) -> dict[str, str]:
    """Return a clean {key: respelling} dict."""
    if not isinstance(lexicon, dict):
        return {}
    out: dict[str, str] = {}
    for k, v in lexicon.items():
        if k is None:
            continue
        key = str(k).strip()
        if not key:
            continue
        out[key] = "" if v is None else str(v)
    return out


def _boundary_prefix(key: str) -> str:
    return r"\b" if key[:1].isalnum() or key[:1] == "_" else ""


def _boundary_suffix(key: str) -> str:
    return r"\b" if key[-1:].isalnum() or key[-1:] == "_" else ""


def _compile(lexicon: dict[str, str]) -> tuple[Optional[re.Pattern], dict[str, str]]:
    """Build the single alternation regex + casefold→respelling lookup."""
    keys = sorted(lexicon.keys(), key=len, reverse=True)
    if not keys:
        return None, {}
    lookup = {k.casefold(): lexicon[k] for k in keys}
    alts = [f"{_boundary_prefix(k)}{re.escape(k)}{_boundary_suffix(k)}" for k in keys]
    pattern = re.compile("(?:" + "|".join(alts) + ")", re.IGNORECASE)
    return pattern, lookup


def apply_lexicon(text: str, lexicon: Optional[dict]) -> str:
    """Replace whole-word occurrences of each lexicon key with its respelling.

    Case-insensitive, word-boundary aware, longest-key-wins, idempotent.
    """
    if not text:
        return text or ""
    clean = normalize_lexicon(lexicon)
    pattern, lookup = _compile(clean)
    if pattern is None:
        return text
    return pattern.sub(lambda m: lookup.get(m.group(0).casefold(), m.group(0)), text)


_INLINE_RE = re.compile(r"\[\[([^\]]{0,256})\]\]")


def apply_inline_overrides(text: str) -> str:
    """Resolve [[term|replacement]] one-off pronunciation overrides."""
    if not text or "[[" not in text:
        return text or ""

    def _repl(m: re.Match) -> str:
        inner = m.group(1)
        if "|" in inner:
            inner = inner.split("|", 1)[1]
        return inner

    return _INLINE_RE.sub(_repl, text)


def apply_pronunciation(
    text: str,
    lexicon: Optional[dict] = None,
) -> str:
    """Apply the pronunciation dictionary + inline overrides to text.

    Order (load-bearing):
      1. Lexicon replacement (whole-word, case-insensitive, longest-first).
      2. Inline [[…]] one-off overrides resolved last.

    This runs AFTER normalize_for_tts() and BEFORE the TTS engine.
    """
    if not text:
        return text or ""
    out = apply_lexicon(text, lexicon) if lexicon else text
    return apply_inline_overrides(out)
