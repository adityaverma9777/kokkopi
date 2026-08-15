"""Audio DSP pipeline — normalization, mastering, and effects.

Ported from VoiceStudio services/audio_dsp.py.

All effects use Spotify's `pedalboard` library. When pedalboard is not
installed, every function degrades gracefully and returns audio unmodified.
This ensures the pipeline never breaks synthesis due to a missing optional dep.
"""
import logging
import torch

logger = logging.getLogger("kokkopi.dsp")

EFFECT_PRESETS = {
    "broadcast": {
        "label": "Broadcast",
        "icon": "📻",
        "description": "Radio/podcast standard — warm, compressed, clear.",
        "chain": [
            {"type": "highpass", "cutoff_hz": 80},
            {"type": "compressor", "threshold_db": -18, "ratio": 3.0, "attack_ms": 5, "release_ms": 80},
            {"type": "eq", "low_gain_db": 1.5, "mid_gain_db": 0, "high_gain_db": 2.0},
            {"type": "limiter", "threshold_db": -1.0},
        ],
    },
    "podcast": {
        "label": "Podcast",
        "icon": "🎙️",
        "description": "Close-mic, intimate — heavy compression, no reverb.",
        "chain": [
            {"type": "highpass", "cutoff_hz": 100},
            {"type": "noise_gate", "threshold_db": -40, "release_ms": 200},
            {"type": "compressor", "threshold_db": -20, "ratio": 4.0, "attack_ms": 2, "release_ms": 60},
            {"type": "eq", "low_gain_db": -1.0, "mid_gain_db": 2.0, "high_gain_db": 1.5},
            {"type": "limiter", "threshold_db": -0.5},
        ],
    },
    "warm": {
        "label": "Warm",
        "icon": "☀️",
        "description": "Boosted low-mids, subtle saturation, cozy feel.",
        "chain": [
            {"type": "highpass", "cutoff_hz": 60},
            {"type": "eq", "low_gain_db": 3.0, "mid_gain_db": 1.0, "high_gain_db": -1.0},
            {"type": "compressor", "threshold_db": -16, "ratio": 2.0, "attack_ms": 8, "release_ms": 120},
            {"type": "reverb", "room_size": 0.15, "wet_level": 0.06, "dry_level": 0.94},
        ],
    },
    "raw": {
        "label": "Raw",
        "icon": "🔇",
        "description": "No processing — model output as-is.",
        "chain": [],
    },
}

MASTERING_CHAIN = [
    {"type": "highpass", "cutoff_hz": 60},
    {"type": "compressor", "threshold_db": -15, "ratio": 1.5, "attack_ms": 2.0, "release_ms": 100},
]


def list_effect_presets() -> list[dict]:
    return [
        {"id": k, "label": v["label"], "icon": v["icon"], "description": v["description"]}
        for k, v in EFFECT_PRESETS.items()
    ]


def get_effect_chain(preset_id: str) -> list[dict]:
    p = EFFECT_PRESETS.get(preset_id)
    return p["chain"] if p else []


def normalize_audio(audio_tensor: torch.Tensor, target_dBFS: float = -2.0) -> torch.Tensor:
    """Peak-normalize audio to a standard broadcasting level.

    Never amplifies near-silent signals (avoids amplifying noise floors
    from failed/dead renders into full-scale hiss).
    """
    if audio_tensor.numel() == 0:
        return audio_tensor
    max_val = torch.abs(audio_tensor).max()
    silence_floor = 10 ** (-50.0 / 20.0)
    if max_val > silence_floor:
        target_amp = 10 ** (target_dBFS / 20.0)
        audio_tensor = audio_tensor * (target_amp / max_val)
    return audio_tensor


def trim_trailing_silence(
    audio_tensor: torch.Tensor,
    sample_rate: int,
    keep_tail_s: float = 0.3,
) -> torch.Tensor:
    """Trim trailing near-silence from a generated clip, keeping a short
    natural tail after the last voiced sample.
    """
    if audio_tensor.numel() == 0:
        return audio_tensor
    floor = 10 ** (-50.0 / 20.0)
    envelope = torch.abs(audio_tensor)
    if envelope.ndim > 1:
        envelope = envelope.amax(dim=tuple(range(envelope.ndim - 1)))
    voiced = torch.nonzero(envelope > floor)
    if voiced.numel() == 0:
        return audio_tensor
    last_voiced = int(voiced[-1].item())
    end = last_voiced + 1 + int(keep_tail_s * sample_rate)
    if end >= audio_tensor.shape[-1]:
        return audio_tensor
    return audio_tensor[..., :end]


def apply_mastering(audio_tensor: torch.Tensor, sample_rate: int = 24000) -> torch.Tensor:
    """Apply broadcast pre-stage (highpass + gentle compression). Degrades gracefully."""
    try:
        return apply_effects_chain(audio_tensor, sample_rate, MASTERING_CHAIN)
    except Exception as e:
        logger.warning("Mastering DSP error: %s", e)
        return audio_tensor


def apply_effects_chain(audio_tensor: torch.Tensor, sample_rate: int, chain: list[dict]) -> torch.Tensor:
    """Apply a chain of named effects to an audio tensor.

    Supported types: highpass, lowpass, compressor, reverb, noise_gate, eq, limiter.
    Unknown types are silently skipped. Degrades gracefully if pedalboard is not installed.
    """
    if not chain:
        return audio_tensor
    try:
        from pedalboard import (
            Pedalboard, Compressor, Reverb, HighpassFilter, LowpassFilter,
            NoiseGate, Limiter, LowShelfFilter, HighShelfFilter, PeakFilter,
        )
        import numpy as np
    except ImportError:
        logger.debug("pedalboard not installed — effects chain skipped")
        return audio_tensor

    plugins = []
    for fx in chain:
        t = fx.get("type", "").lower()
        try:
            if t == "highpass":
                plugins.append(HighpassFilter(cutoff_frequency_hz=fx.get("cutoff_hz", 80)))
            elif t == "lowpass":
                plugins.append(LowpassFilter(cutoff_frequency_hz=fx.get("cutoff_hz", 8000)))
            elif t == "compressor":
                plugins.append(Compressor(
                    threshold_db=fx.get("threshold_db", -15), ratio=fx.get("ratio", 2.0),
                    attack_ms=fx.get("attack_ms", 5), release_ms=fx.get("release_ms", 100),
                ))
            elif t == "reverb":
                plugins.append(Reverb(
                    room_size=fx.get("room_size", 0.2), wet_level=fx.get("wet_level", 0.1),
                    dry_level=fx.get("dry_level", 0.9),
                ))
            elif t == "noise_gate":
                plugins.append(NoiseGate(
                    threshold_db=fx.get("threshold_db", -40), release_ms=fx.get("release_ms", 200),
                ))
            elif t == "limiter":
                plugins.append(Limiter(threshold_db=fx.get("threshold_db", -1.0)))
            elif t == "eq":
                low, mid, high = fx.get("low_gain_db", 0), fx.get("mid_gain_db", 0), fx.get("high_gain_db", 0)
                if low:
                    plugins.append(LowShelfFilter(cutoff_frequency_hz=250, gain_db=low))
                if mid:
                    plugins.append(PeakFilter(cutoff_frequency_hz=1500, gain_db=mid, q=1.0))
                if high:
                    plugins.append(HighShelfFilter(cutoff_frequency_hz=4000, gain_db=high))
        except Exception as e:
            logger.warning("Failed to create %s effect: %s", t, e)

    if not plugins:
        return audio_tensor

    board = Pedalboard(plugins)
    audio_np = audio_tensor.cpu().numpy()
    if audio_np.ndim == 1:
        audio_np = audio_np[None, :]
    try:
        effected = board(audio_np, sample_rate, reset=False)
        return torch.from_numpy(effected).to(audio_tensor.device)
    except Exception as e:
        logger.warning("Effects chain failed: %s — returning unmodified audio", e)
        return audio_tensor
