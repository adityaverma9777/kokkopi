import httpx
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

async def fetch_sitemap_urls(sitemap_url: str, max_urls: int = 1000) -> set[str]:
    """
    Fetches and parses a sitemap or sitemap index.
    Returns a set of discovered URLs.
    """
    discovered_urls = set()
    
    async def _fetch(url: str):
        if len(discovered_urls) >= max_urls:
            return
            
        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                response = await client.get(url)
                response.raise_for_status()
                
                # Check if it's an XML response (sitemaps should be)
                # But sometimes servers return it as text/html or text/xml
                soup = BeautifulSoup(response.content, features="xml")
                
                # Handle Sitemap Indexes
                for sitemap in soup.find_all("sitemap"):
                    loc = sitemap.find("loc")
                    if loc and loc.text:
                        await _fetch(loc.text.strip())
                        
                # Handle URL Sets
                for url_node in soup.find_all("url"):
                    loc = url_node.find("loc")
                    if loc and loc.text:
                        clean_url = loc.text.strip()
                        if clean_url:
                            discovered_urls.add(clean_url)
                            if len(discovered_urls) >= max_urls:
                                break
                                
        except Exception as e:
            print(f"Failed to fetch sitemap {url}: {e}")
            
    await _fetch(sitemap_url)
    return discovered_urls
