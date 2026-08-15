from typing import AsyncGenerator, List, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from db.models import Agent, AgentSetting, ProviderCredential
from .models import AgentContext, AgentResponse, AgentSource
from .retrieval import RetrievalService
from .providers import GroqProvider
from .context import build_context_string
from .prompts import build_system_prompt, format_messages
from .guardrails import check_no_answer, get_no_answer_response
from ingestion.embeddings import SentenceTransformerProvider

# Singleton embedding provider for the FastAPI process
_embed_provider = None

def get_embed_provider() -> SentenceTransformerProvider:
    global _embed_provider
    if _embed_provider is None:
        _embed_provider = SentenceTransformerProvider()
    return _embed_provider

class AgentRuntime:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.retrieval_service = RetrievalService(db, get_embed_provider())

    async def _get_provider_credential(self, tenant_id: str) -> ProviderCredential:
        result = await self.db.execute(
            select(ProviderCredential).where(ProviderCredential.tenant_id == tenant_id, ProviderCredential.provider == "groq")
        )
        cred = result.scalars().first()
        if not cred:
            raise Exception("Agent AI provider is not configured.")
        return cred

    async def _get_agent_and_settings(self, agent_id: str) -> tuple[Agent, AgentSetting]:
        result = await self.db.execute(select(Agent).where(Agent.id == agent_id))
        agent = result.scalars().first()
        if not agent:
            raise Exception("Agent not found.")
            
        settings_res = await self.db.execute(select(AgentSetting).where(AgentSetting.agent_id == agent_id))
        settings = settings_res.scalars().first()
        
        return agent, settings

    async def _prepare_context_and_provider(self, agent_id: str, query: str) -> tuple[AgentContext, GroqProvider]:
        agent, settings = await self._get_agent_and_settings(agent_id)
        cred = await self._get_provider_credential(agent.tenant_id)
        
        # Retrieval (agent-scoped)
        profile = await self.retrieval_service.get_structured_profile(agent_id)
        
        # similarity threshold < 1.0 (cosine distance 1.0 is orthogonal, 0.0 is perfect)
        # We can use 0.5 as a reasonable threshold for MVP. 
        chunks = await self.retrieval_service.get_semantic_chunks(
            agent_id=agent_id, 
            query=query, 
            top_k=5, 
            threshold=0.5
        )
        
        context = AgentContext(
            business_profile=profile,
            retrieved_chunks=chunks,
            agent_settings={"greeting": settings.greeting} if settings else {}
        )
        
        # Initialize Provider
        # Model config hierarchy: settings model -> default
        # But settings model is not in schema yet, so we use the required default
        model = "openai/gpt-oss-120b"
        provider = GroqProvider(encrypted_api_key=cred.encrypted_secret, model=model)
        
        return context, provider

    def _extract_sources(self, chunks: List[Dict]) -> List[AgentSource]:
        sources = []
        seen_urls = set()
        for c in chunks:
            url = c.get("metadata", {}).get("source_url")
            title = c.get("metadata", {}).get("title", "Source Page")
            if url and url not in seen_urls:
                sources.append(AgentSource(title=title, url=url))
                seen_urls.add(url)
        return sources

    async def respond(self, agent_id: str, message: str, history: Optional[List[Dict[str, str]]] = None) -> AgentResponse:
        context, provider = await self._prepare_context_and_provider(agent_id, message)
        
        # Guardrails check
        no_answer = check_no_answer(context, message)
        if no_answer:
            return no_answer
            
        # Build prompt
        sys_prompt = build_system_prompt(context)
        messages = format_messages(sys_prompt, history or [], message)
        
        # Generate
        try:
            response_text = await provider.generate(messages, max_completion_tokens=2048)
            return AgentResponse(
                text=response_text,
                sources=self._extract_sources(context.retrieved_chunks),
                grounded=True
            )
        except Exception as e:
            if "unavailable" in str(e):
                raise
            # generic fallback
            return get_no_answer_response(context)

    async def stream(self, agent_id: str, message: str, history: Optional[List[Dict[str, str]]] = None) -> AsyncGenerator[str, None]:
        context, provider = await self._prepare_context_and_provider(agent_id, message)
        
        no_answer = check_no_answer(context, message)
        if no_answer:
            yield no_answer.text
            return
            
        sys_prompt = build_system_prompt(context)
        messages = format_messages(sys_prompt, history or [], message)
        
        try:
            async for chunk in provider.stream(messages, max_completion_tokens=2048):
                yield chunk
        except Exception as e:
            if "unavailable" in str(e):
                raise
            yield "\n" + get_no_answer_response(context).text
