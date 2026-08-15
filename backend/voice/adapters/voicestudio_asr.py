import asyncio
import os
import sys
from typing import Dict, Any, Optional

# Ensure VoiceStudio is importable
VOICESTUDIO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../../VoiceStudio"))
if VOICESTUDIO_ROOT not in sys.path:
    sys.path.insert(0, VOICESTUDIO_ROOT)

# Import the original VoiceStudio logic
from backend.services.asr_backend import get_active_asr_backend
from backend.services.audio_io import load_audio_bytes

class VoiceStudioASRAdapter:
    """
    Adapter that wraps VoiceStudio's internal ASR engines and provides
    the clean Kokkopi interface.
    """
    def __init__(self):
        self._backend = None

    def _get_backend(self):
        if self._backend is None:
            self._backend = get_active_asr_backend()
        return self._backend

    async def transcribe(self, audio_bytes: bytes, options: Optional[Dict[str, Any]] = None) -> str:
        backend = self._get_backend()
        
        # We need to decode the bytes into a waveform tensor
        waveform, sample_rate = load_audio_bytes(audio_bytes, target_sr=16000)
        
        loop = asyncio.get_running_loop()
        
        kwargs = {}
        if options and "language" in options:
            kwargs["language"] = options["language"]
            
        # Run transcription in a threadpool
        text = await loop.run_in_executor(None, lambda: backend.transcribe(waveform, **kwargs))
        return text

    async def health(self) -> Dict[str, Any]:
        backend = self._get_backend()
        ok, msg = backend.is_available()
        return {
            "status": "ok" if ok else "error",
            "engine": backend.id,
            "message": msg
        }
