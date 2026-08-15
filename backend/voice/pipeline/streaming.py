"""Streaming voice pipeline — the complete LLM→Audio chain.

Architecture:

    Visitor speaks
          ↓
    faster-whisper ASR (asr.py)
          ↓
    AgentRuntime (Groq BYOK)
          ↓
    LLM token stream
          ↓
    SentenceChunker (sentence_chunker.py)    ← streaming sentence boundaries
          ↓
    parse_ssml_lite (ssml_lite.py)           ← resolve [slow]/[spell] markup
          ↓
    normalize_for_tts (text_normalization.py) ← numbers, times, abbrevs
          ↓
    apply_pronunciation (pronunciation.py)   ← custom lexicon
          ↓
    VoiceStudio-derived TTS
          ↓
    normalize_audio + apply_mastering (audio_dsp.py)
          ↓
    WAV bytes → WebSocket → Visitor hears

For non-streaming (full text → audio), use synthesize_full().
"""
from __future__ import annotations

import asyncio
import io
import logging
import os
from typing import AsyncIterator, Optional

import torch

from voice.pipeline.sentence_chunker import SentenceChunker
from voice.pipeline.text_normalization import normalize_for_tts
from voice.pipeline.pronunciation import apply_pronunciation
from voice.pipeline.audio_dsp import normalize_audio, apply_mastering, get_effect_chain, apply_effects_chain
from voice.pipeline.ssml_lite import parse_ssml_lite, apply_ssml_lite_to_text
from voice.pipeline.chunked_tts import split_text_into_chunks, concatenate_audio_chunks

logger = logging.getLogger("kokkopi.voice_pipeline")

SAMPLE_RATE = int(os.environ.get("KOKKOPI_TTS_SAMPLE_RATE", "24000"))


def _tensor_to_wav_bytes(audio: torch.Tensor, sample_rate: int) -> bytes:
    """Convert a float32 audio tensor to raw PCM WAV bytes."""
    import soundfile as sf
    buf = io.BytesIO()
    audio_np = audio.squeeze().cpu().numpy()
    sf.write(buf, audio_np, sample_rate, format="WAV", subtype="PCM_16")
    return buf.getvalue()


def _prepare_sentence_for_tts(
    sentence: str,
    *,
    pronunciation_lexicon: Optional[dict] = None,
    language: str = "en",
) -> str:
    """Full text processing pipeline: SSML → normalize → pronunciation."""
    text = apply_ssml_lite_to_text(sentence)
    text = normalize_for_tts(text, language=language)
    if pronunciation_lexicon:
        text = apply_pronunciation(text, lexicon=pronunciation_lexicon)
    return text.strip()


async def transcribe_audio(audio_bytes: bytes) -> str:
    """Transcribe visitor audio bytes to text using faster-whisper."""
    from voice.pipeline.asr import transcribe
    try:
        return await transcribe(audio_bytes)
    except TimeoutError as e:
        logger.warning("ASR timeout: %s", e)
        return ""
    except Exception as e:
        logger.error("ASR failed: %s", e)
        return ""


async def stream_voice_response(
    text_stream: AsyncIterator[str],
    *,
    voice_service,
    pronunciation_lexicon: Optional[dict] = None,
    dsp_preset: str = "broadcast",
    language: str = "en",
    cancel_event: Optional[asyncio.Event] = None,
) -> AsyncIterator[bytes]:
    """Stream audio chunks from an LLM token stream.

    Yields WAV bytes for each synthesized sentence. The first audio chunk
    arrives as soon as the first sentence is complete, not when the full
    LLM response finishes — giving near-real-time voice output.

    SSML-LITE tags ([slow], [fast], [emphasis], [spell]) in the LLM output
    are resolved before TTS so the engine never sees raw markup.

    Args:
        text_stream: Async iterator of LLM text tokens.
        voice_service: VoiceService instance with .synthesize_tensor(text).
        pronunciation_lexicon: Optional {word: respelling} dict for this agent.
        dsp_preset: Audio effect preset ID (broadcast, podcast, warm, raw).
        language: ISO language code for text normalization.
        cancel_event: Set to interrupt streaming mid-response.
    """
    effect_chain = get_effect_chain(dsp_preset)

    async def _synthesize_sentence(sentence: str) -> Optional[bytes]:
        if not sentence.strip():
            return None
        if cancel_event and cancel_event.is_set():
            return None

        prepared = _prepare_sentence_for_tts(sentence, pronunciation_lexicon=pronunciation_lexicon, language=language)
        if not prepared:
            return None

        try:
            audio_tensor = await voice_service.synthesize_tensor(prepared)
            if audio_tensor is None or audio_tensor.numel() == 0:
                return None

            audio_tensor = normalize_audio(audio_tensor)
            audio_tensor = apply_mastering(audio_tensor)
            if effect_chain:
                audio_tensor = apply_effects_chain(audio_tensor, SAMPLE_RATE, effect_chain)

            return _tensor_to_wav_bytes(audio_tensor, SAMPLE_RATE)
        except Exception as e:
            logger.error("TTS synthesis failed for sentence %r: %s", sentence[:50], e)
            return None

    chunker = SentenceChunker(language=language, aggressive_first_flush=True)

    async for token in text_stream:
        if cancel_event and cancel_event.is_set():
            chunker.reset()
            return

        sentences = chunker.push(token)
        for sentence in sentences:
            chunk = await _synthesize_sentence(sentence)
            if chunk:
                yield chunk

    for sentence in chunker.flush():
        chunk = await _synthesize_sentence(sentence)
        if chunk:
            yield chunk


async def synthesize_full(
    text: str,
    *,
    voice_service,
    pronunciation_lexicon: Optional[dict] = None,
    dsp_preset: str = "broadcast",
    language: str = "en",
) -> bytes:
    """Synthesize a complete text response (non-streaming path).

    Splits into sentence chunks to avoid model degradation on long inputs,
    then crossfades them back into a single WAV.

    Returns WAV bytes.
    """
    effect_chain = get_effect_chain(dsp_preset)
    prepared = _prepare_sentence_for_tts(text, pronunciation_lexicon=pronunciation_lexicon, language=language)
    if not prepared:
        return b""

    chunks_text = split_text_into_chunks(prepared)
    rendered: list[Optional[torch.Tensor]] = []

    for chunk_text in chunks_text:
        try:
            tensor = await voice_service.synthesize_tensor(chunk_text)
            rendered.append(tensor)
        except Exception as e:
            logger.error("TTS chunk failed: %s", e)
            rendered.append(None)

    audio = concatenate_audio_chunks(rendered, SAMPLE_RATE)
    audio = normalize_audio(audio)
    audio = apply_mastering(audio)
    if effect_chain:
        audio = apply_effects_chain(audio, SAMPLE_RATE, effect_chain)

    return _tensor_to_wav_bytes(audio, SAMPLE_RATE)
