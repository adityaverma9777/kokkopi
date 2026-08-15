"""Speaker-clone extraction — diarised segment to per-speaker reference WAV.

Ported from VoiceStudio services/speaker_clone.py.

For the Kokkopi voice agent use-case, this module provides two paths:

1. UPLOAD path (customer provides audio):
   extract_and_save_reference() — validates + saves a user-uploaded audio clip.
   Used by the Voice page "Clone a voice" feature.

2. DIARISED path (programmatic from multi-speaker audio):
   extract_speaker_clones() — picks the longest clean passage per speaker
   from diarized segments (used if we ever add speaker diarization ingestion).

Authorization/consent is ALWAYS required before any cloning. The REST
endpoint enforces this; this module also checks the flag.
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
MIN_SEGMENT_REF_DURATION_S = 3.0
MIN_SLICE_DURATION_S = 1.5
ADJACENT_TURN_GUARD_S = 0.3

VOICE_PROFILES_DIR = Path(os.environ.get("KOKKOPI_VOICE_PROFILES_DIR", "/tmp/kokkopi_voice_profiles"))

_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="kokkopi_clone")


def _adjacent_to_other_speaker(seg: dict, speaker_id: str, all_segments: list[dict] | None) -> bool:
    if not all_segments:
        return False
    s0 = float(seg.get("start", 0.0))
    s1 = float(seg.get("end", 0.0))
    for other in all_segments:
        if other is seg:
            continue
        if (other.get("speaker_id") or "Speaker 1") == speaker_id:
            continue
        o0 = float(other.get("start", 0.0))
        o1 = float(other.get("end", 0.0))
        if max(o0 - s1, s0 - o1) < ADJACENT_TURN_GUARD_S:
            return True
    return False


def _pick_reference_slices(
    items: list[tuple[int, dict]],
    *,
    speaker_id: str | None = None,
    all_segments: list[dict] | None = None,
    labels_source: str | None = None,
) -> list[tuple[int, dict]]:
    if not items:
        return []
    if labels_source == "heuristic":
        return []
    if speaker_id is None:
        speaker_id = items[0][1].get("speaker_id") or "Speaker 1"

    def _dur(pair) -> float:
        return max(0.0, float(pair[1].get("end", 0.0)) - float(pair[1].get("start", 0.0)))

    ranked = sorted(
        items,
        key=lambda pair: (_adjacent_to_other_speaker(pair[1], speaker_id, all_segments), -_dur(pair)),
    )

    picked: list[tuple[int, dict]] = []
    total = 0.0
    for idx, seg in ranked:
        dur = _dur((idx, seg))
        if dur < MIN_SLICE_DURATION_S:
            continue
        if total + dur > MAX_REF_DURATION_S and picked:
            continue
        picked.append((idx, seg))
        total += dur
        if total >= IDEAL_REF_DURATION_S:
            break

    if total < MIN_REF_DURATION_S:
        return []

    picked.sort(key=lambda pair: pair[0])
    return picked


def _concat_slices(audio: np.ndarray, sr: int, picked: list[tuple[int, dict]]) -> np.ndarray:
    parts: list[np.ndarray] = []
    for _, seg in picked:
        start = int(float(seg.get("start", 0.0)) * sr)
        end = int(float(seg.get("end", 0.0)) * sr)
        start = max(0, start)
        end = min(audio.size, end)
        if end <= start:
            continue
        parts.append(audio[start:end])
    if not parts:
        return np.zeros(0, dtype=np.float32)
    gap = np.zeros(int(0.02 * sr), dtype=np.float32)
    out: list[np.ndarray] = []
    for i, part in enumerate(parts):
        if i > 0:
            out.append(gap)
        out.append(part.astype(np.float32, copy=False))
    return np.concatenate(out)


def _safe_name(speaker_id: str) -> str:
    cleaned = []
    for ch in speaker_id.lower():
        if ch.isalnum():
            cleaned.append(ch)
        elif ch in (" ", "-"):
            cleaned.append("_")
    return "".join(cleaned) or "speaker"


def extract_speaker_clones(
    vocals_path: str,
    segments: list[dict],
    out_dir: str,
    *,
    labels_source: str | None = None,
) -> dict[str, dict]:
    """Build a per-speaker reference sample from vocals_path + diarized segments.

    Returns dict keyed by speaker_id:
        {"Speaker 1": {"ref_audio": "/path/voice_speaker_1.wav", "ref_text": "...", "duration": 7.83, "source_count": 2}}

    Speakers with < MIN_REF_DURATION_S are skipped — better to use the
    default TTS voice than a bad clone.
    """
    import soundfile as sf

    if labels_source == "heuristic":
        logger.info("speaker_clone: skipping — speaker labels are gap-based heuristic estimates")
        return {}
    if not vocals_path or not os.path.exists(vocals_path):
        logger.info("speaker_clone: no vocals track at %s; skipping", vocals_path)
        return {}
    if not segments:
        return {}

    try:
        audio, sr = sf.read(vocals_path, dtype="float32", always_2d=False)
    except Exception as e:
        logger.warning("speaker_clone: failed to read %s: %s", vocals_path, e)
        return {}
    if audio.ndim > 1:
        audio = audio.mean(axis=1)

    by_speaker: dict[str, list[tuple[int, dict]]] = {}
    for idx, seg in enumerate(segments):
        spk = seg.get("speaker_id") or "Speaker 1"
        by_speaker.setdefault(spk, []).append((idx, seg))

    os.makedirs(out_dir, exist_ok=True)
    out: dict[str, dict] = {}

    for speaker_id, items in by_speaker.items():
        chosen = _pick_reference_slices(items, speaker_id=speaker_id, all_segments=segments, labels_source=labels_source)
        if not chosen:
            logger.info("speaker_clone: %s has <%ss of usable audio; falling back to default voice", speaker_id, MIN_REF_DURATION_S)
            continue

        ref_audio_np = _concat_slices(audio, sr, chosen)
        if ref_audio_np.size == 0:
            continue

        safe_id = _safe_name(speaker_id)
        ref_path = os.path.join(out_dir, f"voice_{safe_id}.wav")
        try:
            sf.write(ref_path, ref_audio_np, sr)
        except Exception as e:
            logger.warning("speaker_clone: failed to write %s: %s", ref_path, e)
            continue

        ref_text = " ".join((seg.get("text") or "").strip() for _, seg in chosen).strip()
        out[speaker_id] = {
            "ref_audio": ref_path,
            "ref_text": ref_text,
            "duration": float(ref_audio_np.size) / float(sr),
            "source_count": len(chosen),
        }
        logger.info("speaker_clone: wrote %s (%.2fs from %d slice(s))", ref_path, out[speaker_id]["duration"], len(chosen))

    return out


def _validate_and_extract_sync(audio_bytes: bytes) -> dict:
    """Validate audio quality and extract a clean reference segment."""
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
                "message": f"Audio is {duration_s:.1f}s. Minimum is {MIN_REF_DURATION_S}s for a reliable clone.",
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
                "message": "Audio appears silent. Please upload a recording with clear speech.",
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
    """Extract + persist a VoiceProfile from an uploaded audio sample.

    consent_confirmed MUST be True. The cloning UI must not call this without
    displaying and capturing explicit user consent.
    """
    if not consent_confirmed:
        return {
            "status": "error",
            "message": "Voice cloning requires explicit consent authorization.",
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
