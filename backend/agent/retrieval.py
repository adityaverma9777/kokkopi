from typing import List, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import text

from db.models import BusinessProfile, DocumentChunk
from ingestion.embeddings import SentenceTransformerProvider

class RetrievalService:
    def __init__(self, db: AsyncSession, embed_provider: SentenceTransformerProvider):
        self.db = db
        self.embed_provider = embed_provider

    async def get_structured_profile(self, agent_id: str) -> Dict[str, Any]:
        result = await self.db.execute(select(BusinessProfile).where(BusinessProfile.agent_id == agent_id))
        profile = result.scalars().first()
        if not profile:
            return {}
            
        return {
            "business_name": profile.business_name,
            "description": profile.description,
            "industry": profile.industry,
            "phone": profile.phone,
            "email": profile.email,
            "address": profile.address,
            "hours": profile.hours,
            "services": profile.services,
            "faqs": profile.faqs,
            "policies": profile.policies
        }

    async def get_semantic_chunks(self, agent_id: str, query: str, top_k: int = 5, threshold: float = 1.0) -> List[Dict[str, Any]]:
        # Generate query embedding
        query_vector = self.embed_provider.embed_texts([query])[0]
        
        # pgvector uses <-> for L2 distance, <=> for cosine distance, <#> for inner product.
        # all-MiniLM-L6-v2 vectors are typically normalized, so <=> (cosine) or <-> (L2) both work.
        # Cosine distance ranges from 0 (perfect match) to 2 (opposite).
        # We will use cosine distance '<=>'
        
        sql = text("""
            SELECT id, content, metadata_json, (embedding <=> :query_embedding) as distance
            FROM document_chunks
            WHERE agent_id = :agent_id
            AND (embedding <=> :query_embedding) < :threshold
            ORDER BY embedding <=> :query_embedding
            LIMIT :top_k
        """)
        
        result = await self.db.execute(sql, {
            "query_embedding": str(query_vector),
            "agent_id": agent_id,
            "threshold": threshold,
            "top_k": top_k
        })
        
        chunks = []
        for row in result:
            chunks.append({
                "id": str(row.id),
                "content": row.content,
                "metadata": row.metadata_json,
                "distance": row.distance
            })
            
        return chunks
