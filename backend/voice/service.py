import sys
import os
from typing import Optional, Dict, Any, AsyncGenerator

# Ensure VoiceStudio is in the Python path so adapters can import from it
VOICESTUDIO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../VoiceStudio"))
if VOICESTUDIO_ROOT not in sys.path:
    sys.path.insert(0, VOICESTUDIO_ROOT)

from .interface import VoiceBackend
from .adapters.voicestudio_tts import VoiceStudioTTSAdapter
from .adapters.voicestudio_asr import VoiceStudioASRAdapter

class KokkopiVoiceService(VoiceBackend):
    """
    Kokkopi's core voice service. 
    It delegates actual inference to the VoiceStudio adapters.
    """
    def __init__(self):
        self.tts_adapter = VoiceStudioTTSAdapter()
        self.asr_adapter = VoiceStudioASRAdapter()

    async def list_voices(self) -> list[Dict[str, Any]]:
        # Map to TTS adapter
        return await self.tts_adapter.list_voices()

    async def clone_voice(self, sample_path: str, metadata: Dict[str, Any]) -> str:
        # Voice cloning delegation
        return await self.tts_adapter.clone_voice(sample_path, metadata)

    async def design_voice(self, configuration: Dict[str, Any]) -> str:
        return await self.tts_adapter.design_voice(configuration)

    async def synthesize(self, text: str, voice_id: str, options: Optional[Dict[str, Any]] = None) -> bytes:
        return await self.tts_adapter.synthesize(text, voice_id, options)

    async def stream_synthesize(self, text: str, voice_id: str, options: Optional[Dict[str, Any]] = None) -> AsyncGenerator[bytes, None]:
        async for chunk in self.tts_adapter.stream_synthesize(text, voice_id, options):
            yield chunk

    async def transcribe(self, audio_bytes: bytes, options: Optional[Dict[str, Any]] = None) -> str:
        return await self.asr_adapter.transcribe(audio_bytes, options)

    async def health(self) -> Dict[str, Any]:
        tts_health = await self.tts_adapter.health()
        asr_health = await self.asr_adapter.health()
        return {
            "status": "ok" if tts_health.get("status") == "ok" and asr_health.get("status") == "ok" else "degraded",
            "tts": tts_health,
            "asr": asr_health
        }

# Global singleton for the application
voice_service = KokkopiVoiceService()
