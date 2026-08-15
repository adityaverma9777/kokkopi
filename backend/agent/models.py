from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class Message(BaseModel):
    role: str
    content: str

class AgentContext(BaseModel):
    business_profile: Dict[str, Any]
    retrieved_chunks: List[Dict[str, Any]]
    agent_settings: Dict[str, Any]

class AgentSource(BaseModel):
    title: str
    url: str

class AgentResponse(BaseModel):
    text: str
    sources: List[AgentSource]
    grounded: bool
