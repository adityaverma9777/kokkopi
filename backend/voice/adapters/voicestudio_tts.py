import asyncio
import io
import os
import sys
from typing import Dict, Any, Optional, AsyncGenerator

# Ensure VoiceStudio is importable
VOICESTUDIO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../../VoiceStudio"))
if VOICESTUDIO_ROOT not in sys.path:
    sys.path.insert(0, VOICESTUDIO_ROOT)

# Import the original VoiceStudio logic
from backend.services.tts_backend import get_active_tts_backend

class VoiceStudioTTSAdapter:
    """
    Adapter that wraps VoiceStudio's internal TTS engines and provides
    the clean Kokkopi interface.
    """
    def __init__(self):
        # We lazily load the backend so it doesn't block startup
        self._backend = None

    def _get_backend(self):
        if self._backend is None:
            self._backend = get_active_tts_backend()
        return self._backend

    async def list_voices(self) -> list[Dict[str, Any]]:
        # In a real implementation, we would query VoiceStudio's gallery or profiles
        # For now, return a stub
        return [
            {"id": "vstudio_default", "name": "Default OmniVoice", "provider": "voicestudio"}
        ]

    async def clone_voice(self, sample_path: str, metadata: Dict[str, Any]) -> str:
        # Wrap VoiceStudio's speaker_clone logic
        from backend.services.speaker_clone import create_clone_profile
        # We would adapt the async/sync nature here
        return "cloned_voice_123"

    async def design_voice(self, configuration: Dict[str, Any]) -> str:
        return "designed_voice_456"

    async def synthesize(self, text: str, voice_id: str, options: Optional[Dict[str, Any]] = None) -> bytes:
        backend = self._get_backend()
        # VoiceStudio's generate is synchronous and returns a torch.Tensor
        # We run it in a threadpool to not block the FastAPI event loop
        loop = asyncio.get_running_loop()
        
        # kwargs adaptation
        kwargs = {"text": text}
        if options and "speed" in options:
            kwargs["speed"] = options["speed"]
            
        tensor = await loop.run_in_executor(None, lambda: backend.generate(**kwargs))
        
        # Convert tensor to wav bytes using VoiceStudio's audio_io
        from backend.services.audio_io import save_audio_bytes
        wav_bytes = save_audio_bytes(tensor, backend.sample_rate, format="wav")
        return wav_bytes

    async def stream_synthesize(self, text: str, voice_id: str, options: Optional[Dict[str, Any]] = None) -> AsyncGenerator[bytes, None]:
        # For streaming, wrap VoiceStudio's chunked_tts
        from backend.services.chunked_tts import stream_generate
        backend = self._get_backend()
        
        # stream_generate typically yields audio chunks
        # This requires adapting VoiceStudio's generator to async
        # We provide a basic wrapper for demonstration
        generator = stream_generate(backend, text, language="Auto")
        for chunk in generator:
            yield chunk
            await asyncio.sleep(0.01)

    async def health(self) -> Dict[str, Any]:
        backend = self._get_backend()
        ok, msg = backend.is_available()
        return {
            "status": "ok" if ok else "error",
            "engine": backend.id,
            "message": msg
        }
