"""Chunked TTS generation utilities — unlimited-length generation.

Ported from VoiceStudio services/chunked_tts.py.
Adapted from voicebox (https://github.com/jamiepine/voicebox), MIT License.

Splits long text into sentence-boundary chunks and joins per-chunk audio
with a short crossfade. Used when the full response text needs to be
synthesized in one go (non-streaming path), preventing model degradation
from overly long input sequences.

For streaming (sentence-by-sentence), use voice/pipeline/streaming.py.
"""
from __future__ import annotations

import logging
import re
from typing import List

import torch

logger = logging.getLogger("kokkopi.chunked_tts")

DEFAULT_MAX_CHUNK_CHARS = 800
DEFAULT_CROSSFADE_MS = 50

_ABBREVIATIONS = frozenset({
    "mr", "mrs", "ms", "dr", "prof", "sr", "jr", "st", "ave", "blvd",
    "inc", "ltd", "corp", "dept", "est", "approx", "vs", "etc",
    "e.g", "i.e", "a.m", "p.m", "u.s", "u.s.a", "u.k",
})

_BRACKET_TAG_RE = re.compile(r"\[[^\]]*\]")
_SPEAKABLE_RE = re.compile(r"[^\W_]", re.UNICODE)


def _dense_char_count(text: str) -> int:
    n = 0
    for ch in text:
        o = ord(ch)
        if (0x3040 <= o <= 0x30FF or 0x3400 <= o <= 0x4DBF
                or 0x4E00 <= o <= 0x9FFF or 0xAC00 <= o <= 0xD7AF
                or 0xF900 <= o <= 0xFAFF):
            n += 1
    return n


def _effective_max_chars(text: str, max_chars: int) -> int:
    if max_chars <= 0 or not text:
        return max_chars
    dense = _dense_char_count(text)
    if dense and dense / len(text) >= 0.3:
        return max(120, min(max_chars, round(max_chars / 2.5)))
    return max_chars


def _inside_bracket_tag(text: str, pos: int) -> bool:
    for m in _BRACKET_TAG_RE.finditer(text):
        if m.start() < pos < m.end():
            return True
    return False


def _find_last_sentence_end(text: str) -> int:
    best = -1
    for m in re.finditer(r"[.!?](?:\s|$)", text):
        pos = m.start()
        if text[pos] == ".":
            word_start = pos - 1
            while word_start >= 0 and text[word_start].isalpha():
                word_start -= 1
            word = text[word_start + 1: pos].lower()
            if word in _ABBREVIATIONS:
                continue
            if word_start >= 0 and text[word_start].isdigit():
                continue
        if _inside_bracket_tag(text, pos):
            continue
        best = pos
    for m in re.finditer("[\u3002\uff01\uff1f]", text):
        if m.start() > best:
            best = m.start()
    return best


def _find_last_clause_boundary(text: str) -> int:
    best = -1
    for m in re.finditer(r"[;:,—](?:\s|$)", text):
        if _inside_bracket_tag(text, m.start()):
            continue
        best = m.start()
    return best


def _safe_hard_cut(segment: str, max_chars: int) -> int:
    cut = max_chars - 1
    for m in _BRACKET_TAG_RE.finditer(segment):
        if m.start() < cut < m.end():
            return m.start() - 1 if m.start() > 0 else cut
    return cut


def _merge_unspeakable(chunks: List[str], max_chars: int = 0) -> List[str]:
    if len(chunks) < 2:
        return chunks
    out: List[str] = []
    for chunk in chunks:
        if _SPEAKABLE_RE.search(chunk) or not out:
            out.append(chunk)
            continue
        merged = f"{out[-1]} {chunk}"
        if max_chars <= 0 or len(merged) <= max_chars:
            out[-1] = merged
            continue
        head, sep, last_word = out[-1].rpartition(" ")
        if sep and head and _SPEAKABLE_RE.search(last_word):
            out[-1] = head
            out.append(f"{last_word} {chunk}")
        else:
            out[-1] = merged
    if len(out) > 1 and not _SPEAKABLE_RE.search(out[0]):
        merged = f"{out[0]} {out[1]}"
        if max_chars <= 0 or len(merged) <= max_chars:
            out[1] = merged
            out.pop(0)
        else:
            first_word, sep, tail = out[1].partition(" ")
            if sep and tail and _SPEAKABLE_RE.search(first_word):
                out[0] = f"{out[0]} {first_word}"
                out[1] = tail
            else:
                out[1] = merged
                out.pop(0)
    return out


def split_text_into_chunks(text: str, max_chars: int = DEFAULT_MAX_CHUNK_CHARS) -> List[str]:
    """Split text at natural boundaries into chunks of at most max_chars.

    Priority: sentence-end → clause boundary → whitespace → hard cut.
    CJK/kana/Hangul text gets a smaller limit (dense speech per char).
    """
    text = text.strip()
    if not text:
        return []
    max_chars = _effective_max_chars(text, max_chars)
    if max_chars <= 0 or len(text) <= max_chars:
        return [text]

    chunks: List[str] = []
    remaining = text

    while remaining:
        remaining = remaining.lstrip()
        if not remaining:
            break
        if len(remaining) <= max_chars:
            chunks.append(remaining)
            break

        segment = remaining[:max_chars]
        split_pos = _find_last_sentence_end(segment)
        if split_pos == -1:
            split_pos = _find_last_clause_boundary(segment)
        if split_pos == -1:
            split_pos = segment.rfind(" ")
        if split_pos == -1:
            split_pos = _safe_hard_cut(segment, max_chars)

        chunk = remaining[:split_pos + 1].strip()
        if chunk:
            chunks.append(chunk)
        remaining = remaining[split_pos + 1:]

    return _merge_unspeakable(chunks, max_chars)


def _normalize_chunk_shapes(chunks: list) -> list:
    """Coerce mixed-rank/mixed-channel chunks to one concat-compatible shape."""
    target = max(c.dim() for c in chunks)
    if any(c.dim() != target for c in chunks):
        promoted = []
        for c in chunks:
            while c.dim() < target:
                c = c.unsqueeze(0)
            promoted.append(c)
        chunks = promoted
    if target > 1:
        lead = tuple(max(c.shape[i] for c in chunks) for i in range(target - 1))
        chunks = [c if tuple(c.shape[:-1]) == lead else c.expand(*lead, -1) for c in chunks]
    return chunks


def concatenate_audio_chunks(
    chunks: list,
    sample_rate: int,
    *,
    crossfade_ms: int = DEFAULT_CROSSFADE_MS,
) -> torch.Tensor:
    """Join per-chunk waveforms with a linear crossfade on the sample axis.

    Empty chunks are dropped. crossfade_ms=0 is a hard concat.
    """
    kept = [c for c in chunks if c is not None and c.shape[-1] > 0]
    dropped = len(chunks) - len(kept)
    if dropped:
        logger.warning("Dropped %d of %d chunk(s): engine returned no audio for them.", dropped, len(chunks))

    if not kept:
        return torch.zeros(1, dtype=torch.float32)
    if len(kept) == 1:
        return kept[0]

    kept = _normalize_chunk_shapes(kept)
    crossfade_samples = int(sample_rate * crossfade_ms / 1000)
    result = kept[0]

    for chunk in kept[1:]:
        chunk = chunk.to(device=result.device, dtype=result.dtype)
        overlap = min(crossfade_samples, result.shape[-1], chunk.shape[-1])
        if overlap > 0:
            fade_out = torch.linspace(1.0, 0.0, overlap, dtype=result.dtype, device=result.device)
            fade_in = torch.linspace(0.0, 1.0, overlap, dtype=result.dtype, device=result.device)
            blended = result[..., -overlap:] * fade_out + chunk[..., :overlap] * fade_in
            result = torch.cat([result[..., :-overlap], blended, chunk[..., overlap:]], dim=-1)
        else:
            result = torch.cat([result, chunk], dim=-1)

    return result
