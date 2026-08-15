import asyncio
import httpx
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, urldefrag
from typing import Set, List, Dict, Optional
import time

class CrawlerConfig:
    def __init__(self, 
                 max_pages: int = 200, 
                 max_depth: int = 3, 
                 timeout_sec: float = 10.0,
                 max_size_bytes: int = 5 * 1024 * 1024): # 5MB
        self.max_pages = max_pages
        self.max_depth = max_depth
        self.timeout_sec = timeout_sec
        self.max_size_bytes = max_size_bytes

class CrawledPage:
    def __init__(self, url: str, status_code: int, html: str, depth: int):
        self.url = url
        self.status_code = status_code
        self.html = html
        self.depth = depth

class DeterministicCrawler:
    def __init__(self, start_url: str, config: CrawlerConfig = CrawlerConfig()):
        self.start_url = start_url
        self.config = config
        self.base_domain = urlparse(start_url).netloc
        self.visited_urls: Set[str] = set()
        self.pages: List[CrawledPage] = []
        self.failed_count = 0
        self.client = httpx.AsyncClient(timeout=config.timeout_sec, follow_redirects=True)
        
    def _normalize_url(self, raw_url: str) -> str:
        """Removes fragments and normalizes."""
        defragged, _ = urldefrag(raw_url)
        return defragged.rstrip('/')

    def _is_same_domain(self, url: str) -> bool:
        return urlparse(url).netloc == self.base_domain

    def _is_valid_type(self, content_type: str) -> bool:
        if not content_type:
            return True
        return "text/html" in content_type.lower()

    async def crawl(self, seed_urls: Optional[List[str]] = None) -> List[CrawledPage]:
        """
        Crawls starting from seed_urls or start_url if none provided.
        Returns a list of successfully fetched pages.
        """
        queue = [(self._normalize_url(u), 0) for u in (seed_urls or [self.start_url])]
        
        while queue and len(self.visited_urls) < self.config.max_pages:
            url, depth = queue.pop(0)
            
            if url in self.visited_urls:
                continue
                
            self.visited_urls.add(url)
            
            if depth > self.config.max_depth:
                continue

            try:
                # Rate limit sleep could be added here
                # await asyncio.sleep(0.5)
                
                # Use HEAD or stream to check size/type if strict, but for MVP simple GET is fine
                response = await self.client.get(url)
                
                # Check response size roughly
                if len(response.content) > self.config.max_size_bytes:
                    print(f"Skipping {url}: too large")
                    self.failed_count += 1
                    continue
                    
                # Check content type
                if not self._is_valid_type(response.headers.get("content-type", "")):
                    print(f"Skipping {url}: not HTML")
                    # Count as success if we gracefully skip an image
                    continue

                if response.status_code >= 400:
                    print(f"Failed {url}: HTTP {response.status_code}")
                    self.failed_count += 1
                    continue

                html = response.text
                self.pages.append(CrawledPage(url, response.status_code, html, depth))
                
                # Extract links if we can go deeper
                if depth < self.config.max_depth:
                    soup = BeautifulSoup(html, "html.parser")
                    for a_tag in soup.find_all("a", href=True):
                        next_url = urljoin(url, a_tag['href'])
                        next_url = self._normalize_url(next_url)
                        
                        if (self._is_same_domain(next_url) and 
                            next_url not in self.visited_urls and 
                            next_url.startswith("http")):
                            queue.append((next_url, depth + 1))
                            
            except Exception as e:
                print(f"Error crawling {url}: {e}")
                self.failed_count += 1

        await self.client.aclose()
        return self.pages
