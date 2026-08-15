import os
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import List, Optional, Any, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from db.database import get_db
from db.models import Tenant, Agent, CrawlJob, Source, DocumentChunk, BusinessProfile
from auth.dependencies import get_current_tenant

from redis import Redis
from rq import Queue
from tasks import ingest_job

router = APIRouter(prefix="/api/agents", tags=["ingestion"])

# Connect to Redis for Queue
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
redis_conn = Redis.from_url(redis_url)
q = Queue(connection=redis_conn)

class IngestRequest(BaseModel):
    url: Optional[str] = None
    sitemap_url: Optional[str] = None
    consent: bool

class IngestResponse(BaseModel):
    job_id: str
    status: str

class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    total_discovered: int
    total_processed: int
    total_failed: int
    error: Optional[str]

async def _verify_agent_tenant(agent_id: str, tenant_id: str, db: AsyncSession):
    result = await db.execute(select(Agent).where(Agent.id == agent_id, Agent.tenant_id == tenant_id))
    agent = result.scalars().first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found or access denied")
    return agent

@router.post("/{agent_id}/ingest", response_model=IngestResponse)
async def ingest_knowledge(
    agent_id: str, 
    req: IngestRequest, 
    tenant: Tenant = Depends(get_current_tenant), 
    db: AsyncSession = Depends(get_db)
):
    await _verify_agent_tenant(agent_id, tenant.id, db)
    
    if not req.consent:
        raise HTTPException(status_code=400, detail="Explicit consent is required")
        
    if req.url and req.sitemap_url:
        raise HTTPException(status_code=400, detail="Provide url OR sitemap_url, not both")
        
    source_url = req.url or req.sitemap_url
    if not source_url:
        raise HTTPException(status_code=400, detail="Must provide url or sitemap_url")

    # Create Job
    job = CrawlJob(
        agent_id=agent_id,
        source_url=source_url,
        status="queued"
    )
    db.add(job)
    await db.commit()
    
    # Enqueue to RQ
    q.enqueue(ingest_job, str(job.id))
    
    return {"job_id": str(job.id), "status": "queued"}

@router.get("/{agent_id}/ingest/{job_id}", response_model=JobStatusResponse)
async def get_ingest_status(
    agent_id: str, 
    job_id: str,
    tenant: Tenant = Depends(get_current_tenant), 
    db: AsyncSession = Depends(get_db)
):
    await _verify_agent_tenant(agent_id, tenant.id, db)
    
    result = await db.execute(select(CrawlJob).where(CrawlJob.id == job_id, CrawlJob.agent_id == agent_id))
    job = result.scalars().first()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    return {
        "job_id": str(job.id),
        "status": job.status,
        "total_discovered": job.total_discovered or 0,
        "total_processed": job.total_processed or 0,
        "total_failed": job.total_failed or 0,
        "error": job.error
    }

@router.get("/{agent_id}/sources")
async def list_sources(agent_id: str, tenant: Tenant = Depends(get_current_tenant), db: AsyncSession = Depends(get_db)):
    await _verify_agent_tenant(agent_id, tenant.id, db)
    
    result = await db.execute(select(Source).where(Source.agent_id == agent_id))
    sources = result.scalars().all()
    
    return [{"id": str(s.id), "url": s.url, "source_type": s.source_type, "status": s.status} for s in sources]

@router.get("/{agent_id}/knowledge")
async def list_knowledge(agent_id: str, tenant: Tenant = Depends(get_current_tenant), db: AsyncSession = Depends(get_db)):
    await _verify_agent_tenant(agent_id, tenant.id, db)
    
    # Limit to 50 for MVP preview
    result = await db.execute(select(DocumentChunk).where(DocumentChunk.agent_id == agent_id).limit(50))
    chunks = result.scalars().all()
    
    return [
        {
            "id": str(c.id), 
            "content": c.content[:100] + "...", 
            "metadata": c.metadata_json,
            "has_embedding": c.embedding is not None
        } for c in chunks
    ]

@router.get("/{agent_id}/profile")
async def get_profile(agent_id: str, tenant: Tenant = Depends(get_current_tenant), db: AsyncSession = Depends(get_db)):
    await _verify_agent_tenant(agent_id, tenant.id, db)
    
    result = await db.execute(select(BusinessProfile).where(BusinessProfile.agent_id == agent_id))
    profile = result.scalars().first()
    
    if not profile:
        return {}
        
    return {
        "business_name": profile.business_name,
        "description": profile.description,
        "industry": profile.industry,
        "phone": profile.phone,
        "email": profile.email,
        "website": profile.website,
        "address": profile.address,
        "hours": profile.hours,
        "services": profile.services,
        "faqs": profile.faqs
    }

@router.post("/{agent_id}/reindex")
async def reindex(agent_id: str, req: IngestRequest, tenant: Tenant = Depends(get_current_tenant), db: AsyncSession = Depends(get_db)):
    # For MVP, reindex just triggers another ingest
    return await ingest_knowledge(agent_id, req, tenant, db)
