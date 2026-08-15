import asyncio
import os
from ingestion.pipeline import run_ingestion_pipeline

def ingest_job(job_id: str):
    """
    Synchronous wrapper for RQ to execute the async ingestion pipeline.
    """
    asyncio.run(run_ingestion_pipeline(job_id))
