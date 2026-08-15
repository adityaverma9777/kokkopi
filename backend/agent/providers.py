import json
import httpx
from abc import ABC, abstractmethod
from typing import List, Dict, Any, AsyncGenerator

from auth.encryption import decrypt_secret

class LLMProvider(ABC):
    @abstractmethod
    async def generate(self, messages: List[Dict[str, str]], **options) -> str:
        pass

    @abstractmethod
    async def stream(self, messages: List[Dict[str, str]], **options) -> AsyncGenerator[str, None]:
        pass

class GroqProvider(LLMProvider):
    def __init__(self, encrypted_api_key: str, model: str = "openai/gpt-oss-120b"):
        self.api_key = decrypt_secret(encrypted_api_key)
        self.model = model
        self.base_url = "https://api.groq.com/openai/v1/chat/completions"

    async def generate(self, messages: List[Dict[str, str]], **options) -> str:
        max_completion_tokens = options.get("max_completion_tokens", 2048)
        temperature = options.get("temperature", 0.0)

        payload = {
            "model": self.model,
            "messages": messages,
            "max_completion_tokens": max_completion_tokens,
            "temperature": temperature,
            "stream": False
        }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(self.base_url, json=payload, headers=headers)
            if resp.status_code != 200:
                raise Exception("The agent's AI provider credential is unavailable.")
                
            data = resp.json()
            return data["choices"][0]["message"]["content"]

    async def stream(self, messages: List[Dict[str, str]], **options) -> AsyncGenerator[str, None]:
        max_completion_tokens = options.get("max_completion_tokens", 2048)
        temperature = options.get("temperature", 0.0)

        payload = {
            "model": self.model,
            "messages": messages,
            "max_completion_tokens": max_completion_tokens,
            "temperature": temperature,
            "stream": True
        }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            async with client.stream("POST", self.base_url, json=payload, headers=headers) as resp:
                if resp.status_code != 200:
                    raise Exception("The agent's AI provider credential is unavailable.")
                    
                async for line in resp.aiter_lines():
                    line = line.strip()
                    if line.startswith("data: ") and line != "data: [DONE]":
                        raw_data = line[6:]
                        try:
                            chunk = json.loads(raw_data)
                            delta = chunk["choices"][0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                yield content
                        except Exception:
                            pass
