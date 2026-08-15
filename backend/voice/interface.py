from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, AsyncGenerator

class VoiceBackend(ABC):
    """
    Stable internal interface for Kokkopi's voice capabilities.
    Implementations of this interface (adapters) wrap the underlying VoiceStudio 
    or third-party engines.
    """
    
    @abstractmethod
    async def list_voices(self) -> list[Dict[str, Any]]:
        """Return a list of available voices."""
        pass

    @abstractmethod
    async def clone_voice(self, sample_path: str, metadata: Dict[str, Any]) -> str:
        """
        Process an audio sample and return a unique voice_id.
        Raises an exception if the sample is invalid.
        """
        pass

    @abstractmethod
    async def design_voice(self, configuration: Dict[str, Any]) -> str:
        """
        Generate a new voice profile from a configuration (e.g., gender, age, pitch).
        Returns a unique voice_id.
        """
        pass

    @abstractmethod
    async def synthesize(self, text: str, voice_id: str, options: Optional[Dict[str, Any]] = None) -> bytes:
        """
        Synthesize text to audio. Returns complete audio payload (e.g., WAV/MP3 bytes).
        """
        pass

    @abstractmethod
    async def stream_synthesize(self, text: str, voice_id: str, options: Optional[Dict[str, Any]] = None) -> AsyncGenerator[bytes, None]:
        """
        Synthesize text to audio as a stream of byte chunks.
        """
        pass

    @abstractmethod
    async def transcribe(self, audio_bytes: bytes, options: Optional[Dict[str, Any]] = None) -> str:
        """
        Convert audio bytes to text (STT/ASR).
        """
        pass

    @abstractmethod
    async def health(self) -> Dict[str, Any]:
        """
        Return the health status of the voice backend.
        """
        pass
