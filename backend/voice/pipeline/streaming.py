"""Streaming voice pipeline — the complete LLM→Audio chain.

Architecture:

    Visitor speaks
          ↓
    faster-whisper (asr.py)
          ↓
    AgentRuntime (agent/runtime.py)
          ↓
    Groq BYOK → LLM token stream
          ↓
    SentenceChunker (sentence_chunker.py)
          ↓
    normalize_for_tts (text_normalization.py)
          ↓
    apply_pronunciation (pronunciation.py)
          ↓
    VoiceStudio-derived TTS
          ↓
    normalize_audio + apply_mastering (audio_dsp.py)
          ↓
    Streaming WebSocket → Visitor hears

Key design decisions:
  - ASR and TTS run in separate thread pool executors to avoid GIL contention.
  - SentenceChunker drives TTS sentence-by-sentence for low TTFA.
  - Each audio chunk is streamed immediately after generation (no buffering).
  - Cancellation is handled via an asyncio.Event so interrupted sessions
    don't leak model resources.
  - Text normalization and pronunciation run synchronously between chunker
    and TTS — they are CPU-only and fast.
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
from voice.pipeline.audio_dsp import normalize_audio, apply_mastering

logger = logging.getLogger("kokkopi.voice_pipeline")

SAMPLE_RATE = int(os.environ.get("KOKKOPI_TTS_SAMPLE_RATE", "24000"))


def _tensor_to_wav_bytes(audio: torch.Tensor, sample_rate: int) -> bytes:
    """Convert a float32 audio tensor to raw PCM WAV bytes for WebSocket streaming."""
    import soundfile as sf
    buf = io.BytesIO()
    audio_np = audio.squeeze().cpu().numpy()
    sf.write(buf, audio_np, sample_rate, format="WAV", subtype="PCM_16")
    return buf.getvalue()


async def transcribe_audio(audio_bytes: bytes) -> str:
    """Transcribe visitor audio bytes to text using faster-whisper.

    Returns empty string if audio is silent or transcription fails.
    """
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

    Consumes `text_stream` token-by-token. Uses SentenceChunker to batch
    tokens into complete sentences, then pipes each sentence through:
      1. Text normalization (numbers, times, abbreviations)
      2. Pronunciation substitution (custom lexicon)
      3. TTS synthesis
      4. Audio DSP (normalization + mastering)
      5. WAV bytes → yield to caller

    Yields WAV bytes chunks as they are generated. The first chunk arrives
    after the first complete sentence is synthesized — not after the full
    LLM response, giving near-real-time voice output.

    Args:
        text_stream: Async iterator of LLM text tokens.
        voice_service: VoiceService instance (from voice/service.py).
        pronunciation_lexicon: Optional {word: respelling} dict for this agent.
        dsp_preset: Audio effect preset ID (broadcast, podcast, warm, raw).
        language: ISO language code for text normalization.
        cancel_event: Set this event to interrupt streaming mid-response.
    """
    from voice.pipeline.audio_dsp import get_effect_chain, apply_effects_chain

    chunker = SentenceChunker(language=language, aggressive_first_flush=True)
    effect_chain = get_effect_chain(dsp_preset)

    async def _synthesize_sentence(sentence: str) -> Optional[bytes]:
        """Run a single sentence through the full text→audio pipeline."""
        if not sentence.strip():
            return None
        if cancel_event and cancel_event.is_set():
            return None

        normalized = normalize_for_tts(sentence, language=language)
        if pronunciation_lexicon:
            normalized = apply_pronunciation(normalized, lexicon=pronunciation_lexicon)

        if not normalized.strip():
            return None

        try:
            audio_tensor = await voice_service.synthesize_tensor(normalized)
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
