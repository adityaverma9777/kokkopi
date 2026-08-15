import asyncio
import hashlib
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from db.database import AsyncSessionLocal
from db.models import CrawlJob, Source, Document, DocumentChunk, BusinessProfile
from .crawler import DeterministicCrawler, CrawlerConfig
from .sitemap import fetch_sitemap_urls
from .cleaner import clean_html
from .extractor import extract_business_profile
from .chunker import chunk_text
from .embeddings import SentenceTransformerProvider

def _compute_hash(content: str) -> str:
    return hashlib.sha256(content.encode('utf-8')).hexdigest()

async def run_ingestion_pipeline(job_id: str):
    """
    Executes the ingestion pipeline. Runs asynchronously within the RQ worker process.
    """
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(CrawlJob).where(CrawlJob.id == job_id))
        job = result.scalars().first()
        if not job:
            return
            
        agent_id = job.agent_id
        source_url = job.source_url
        
        job.status = "discovering"
        await db.commit()
        
        try:
            # 1. Discover URLs
            seed_urls = None
            if source_url.endswith("xml"):
                seed_urls = list(await fetch_sitemap_urls(source_url))
                job.total_discovered = len(seed_urls)
            else:
                seed_urls = [source_url]
                
            job.status = "crawling"
            await db.commit()
            
            # 2. Crawl Pages
            crawler = DeterministicCrawler(start_url=source_url, config=CrawlerConfig())
            crawled_pages = await crawler.crawl(seed_urls=seed_urls)
            job.total_processed = len(crawled_pages)
            job.total_failed = crawler.failed_count
            
            if not crawled_pages:
                job.status = "failed"
                job.error = "No pages crawled"
                await db.commit()
                return

            job.status = "processing"
            await db.commit()

            # 3. Process Pages & Extract Business Profile
            cleaned_texts = []
            html_contents = []
            valid_pages = []
            
            for page in crawled_pages:
                html_contents.append(page.html)
                clean_txt = clean_html(page.html)
                cleaned_texts.append(clean_txt)
                valid_pages.append((page, clean_txt))
                
            # Extract Profile
            profile_data = extract_business_profile(html_contents)
            
            # Save Profile
            result_prof = await db.execute(select(BusinessProfile).where(BusinessProfile.agent_id == agent_id))
            profile = result_prof.scalars().first()
            if not profile:
                profile = BusinessProfile(agent_id=agent_id)
                db.add(profile)
                
            for k, v in profile_data.items():
                setattr(profile, k, v)
                
            await db.commit()
            
            job.status = "indexing"
            await db.commit()
            
            # 4. Chunk & Embed
            embed_provider = SentenceTransformerProvider()
            
            for page, clean_txt in valid_pages:
                content_hash = _compute_hash(clean_txt)
                
                # Check for duplicate
                result_doc = await db.execute(
                    select(Document).where(Document.agent_id == agent_id, Document.url == page.url)
                )
                existing_doc = result_doc.scalars().first()
                
                if existing_doc and existing_doc.content_hash == content_hash:
                    # Skip duplicate
                    continue
                    
                # Create/Update Source
                result_src = await db.execute(
                    select(Source).where(Source.agent_id == agent_id, Source.url == page.url)
                )
                src = result_src.scalars().first()
                if not src:
                    src = Source(agent_id=agent_id, url=page.url, source_type="webpage")
                    db.add(src)
                    await db.flush()
                
                # Delete old document if it existed
                if existing_doc:
                    await db.delete(existing_doc)
                    await db.flush()
                    
                # Create Document
                doc = Document(
                    agent_id=agent_id,
                    source_id=src.id,
                    url=page.url,
                    text=clean_txt,
                    content_hash=content_hash
                )
                db.add(doc)
                await db.flush()
                
                # Chunking
                chunks = chunk_text(clean_txt, source_url=page.url)
                
                if not chunks:
                    continue
                    
                # Embedding
                texts_to_embed = [c.content for c in chunks]
                vectors = embed_provider.embed_texts(texts_to_embed)
                
                # Save Chunks
                for i, c in enumerate(chunks):
                    doc_chunk = DocumentChunk(
                        agent_id=agent_id,
                        document_id=doc.id,
                        content=c.content,
                        chunk_index=c.index,
                        token_count=len(c.content) // 4,
                        metadata_json=c.metadata,
                        embedding=vectors[i]
                    )
                    db.add(doc_chunk)
                    
                await db.commit()
            
            job.status = "completed"
            await db.commit()
            
        except Exception as e:
            job.status = "failed"
            job.error = str(e)
            await db.commit()
