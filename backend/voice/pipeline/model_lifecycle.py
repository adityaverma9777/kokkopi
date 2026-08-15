"""Model lifecycle manager — lazy loading, memory tracking, and basic routing.

Prevents the ASR and TTS models from being loaded simultaneously until
VRAM budget allows it. Provides a simple registry so other modules can
check model states without importing each model directly.

VRAM Budget (configurable via env):
    KOKKOPI_VRAM_BUDGET_MB — total VRAM available (default: 6000 MB for HF GPU).
    Models are loaded lazily. If adding a model would exceed the budget,
    the oldest loaded model is evicted first.

This is intentionally simple — not a full GPU scheduler. The goal is to
prevent OOM crashes from Whisper + TTS coexisting without coordination.
"""
from __future__ import annotations

import logging
import os
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger("kokkopi.model_lifecycle")

VRAM_BUDGET_MB = float(os.environ.get("KOKKOPI_VRAM_BUDGET_MB", "6000"))

_KNOWN_MODEL_VRAM_MB: dict[str, float] = {
    "asr:tiny": 150,
    "asr:base": 290,
    "asr:small": 480,
    "asr:medium": 1500,
    "asr:large-v3": 3000,
    "tts:voicestudio": 2500,
}


@dataclass
class ModelEntry:
    name: str
    vram_mb: float
    loaded_at: float = field(default_factory=time.time)
    last_used: float = field(default_factory=time.time)
    instance: Any = None


class ModelRegistry:
    """Thread-safe registry tracking loaded model instances."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._models: dict[str, ModelEntry] = {}

    def register(self, name: str, instance: Any, *, vram_mb: Optional[float] = None) -> None:
        mb = vram_mb or _KNOWN_MODEL_VRAM_MB.get(name, 0)
        with self._lock:
            self._evict_if_needed(mb)
            self._models[name] = ModelEntry(name=name, vram_mb=mb, instance=instance)
        logger.info("Model registered: %s (%.0f MB VRAM)", name, mb)

    def get(self, name: str) -> Optional[Any]:
        with self._lock:
            entry = self._models.get(name)
            if entry:
                entry.last_used = time.time()
                return entry.instance
        return None

    def unload(self, name: str) -> bool:
        with self._lock:
            entry = self._models.pop(name, None)
        if entry:
            logger.info("Model unloaded: %s", name)
            return True
        return False

    def _evict_if_needed(self, needed_mb: float) -> None:
        """Evict least-recently-used models if adding `needed_mb` would exceed budget."""
        current_total = sum(e.vram_mb for e in self._models.values())
        while current_total + needed_mb > VRAM_BUDGET_MB and self._models:
            lru_name = min(self._models, key=lambda k: self._models[k].last_used)
            evicted = self._models.pop(lru_name)
            current_total -= evicted.vram_mb
            logger.warning(
                "VRAM budget (%.0f MB) exceeded — evicting '%s' (%.0f MB) to make room for new model.",
                VRAM_BUDGET_MB, lru_name, evicted.vram_mb,
            )

    def status(self) -> list[dict]:
        with self._lock:
            return [
                {
                    "name": e.name,
                    "vram_mb": e.vram_mb,
                    "loaded_at": e.loaded_at,
                    "last_used": e.last_used,
                }
                for e in self._models.values()
            ]

    @property
    def total_vram_used_mb(self) -> float:
        with self._lock:
            return sum(e.vram_mb for e in self._models.values())


registry = ModelRegistry()
