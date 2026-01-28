"""Web content scraping with HTML parsing."""
import asyncio
import logging
from typing import Optional
import httpx
from bs4 import BeautifulSoup

from .models import FetchResult, IndexingConfig

logger = logging.getLogger(__name__)


class WebScraper:
    """HTTP fetcher with HTML content extraction."""
    
    def __init__(self, config: Optional[IndexingConfig] = None):
        """
        Initialize web scraper.
        
        Args:
            config: Indexing configuration
        """
        self.config = config or IndexingConfig()
        self._client: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    async def connect(self):
        """Initialize HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self.config.request_timeout,
                follow_redirects=True,
                headers={
                    "User-Agent": self.config.user_agent,
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.5",
                }
            )
    
    async def close(self):
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def fetch(self, url: str, metadata: Optional[dict] = None) -> FetchResult:
        """
        Fetch a URL and extract text content.
        
        Args:
            url: URL to fetch
            metadata: Additional metadata to include
            
        Returns:
            FetchResult with content or error
        """
        if self._client is None:
            await self.connect()
        
        metadata = metadata or {}
        
        for attempt in range(self.config.max_retries):
            try:
                response = await self._client.get(url)
                
                # Log redirects (301, 302, etc.)
                if response.history:
                    for redirect in response.history:
                        if redirect.status_code in (301, 302, 307, 308):
                            logger.warning(
                                f"Redirect {redirect.status_code} detected: {url} -> {response.url}"
                            )
                
                response.raise_for_status()
                
                content_type = response.headers.get("content-type", "")
                raw_content = response.text
                
                # Extract text from HTML
                if "text/html" in content_type:
                    content = self._extract_html_content(raw_content)
                    title = self._extract_title(raw_content)
                else:
                    content = raw_content
                    title = None
                
                # Truncate if too long
                if len(content) > self.config.max_content_length:
                    content = content[:self.config.max_content_length] + "\n\n[Content truncated]"
                
                result_metadata = {
                    **metadata,
                    "url": url,
                    "source": "web",
                }
                if title:
                    result_metadata["title"] = title
                
                return FetchResult(
                    url=url,
                    success=True,
                    content=content,
                    content_type=content_type,
                    status_code=response.status_code,
                    metadata=result_metadata,
                )
                
            except httpx.HTTPStatusError as e:
                logger.warning(f"HTTP error fetching {url}: {e.response.status_code}")
                if attempt == self.config.max_retries - 1:
                    return FetchResult(
                        url=url,
                        success=False,
                        status_code=e.response.status_code,
                        error=f"HTTP {e.response.status_code}",
                        metadata=metadata,
                    )
                await asyncio.sleep(self.config.request_delay * (attempt + 1))
                
            except Exception as e:
                logger.warning(f"Error fetching {url}: {e}")
                if attempt == self.config.max_retries - 1:
                    return FetchResult(
                        url=url,
                        success=False,
                        error=str(e),
                        metadata=metadata,
                    )
                await asyncio.sleep(self.config.request_delay * (attempt + 1))
        
        # Should not reach here
        return FetchResult(
            url=url,
            success=False,
            error="Max retries exceeded",
            metadata=metadata,
        )
    
    def _extract_html_content(self, html: str) -> str:
        """
        Extract readable text from HTML.
        
        Args:
            html: Raw HTML content
            
        Returns:
            Cleaned text content
        """
        soup = BeautifulSoup(html, "lxml")
        
        # Remove unwanted elements
        for tag in soup.find_all(["script", "style", "nav", "header", "footer", 
                                   "aside", "noscript", "iframe", "svg"]):
            tag.decompose()
        
        # Try to find main content area
        main_content = (
            soup.find("main") or 
            soup.find("article") or 
            soup.find(class_=["content", "main-content", "documentation", "doc-content"]) or
            soup.find(id=["content", "main-content", "documentation", "doc-content"]) or
            soup.find("body")
        )
        
        if main_content:
            text = main_content.get_text(separator=" ", strip=True)
        else:
            text = soup.get_text(separator=" ", strip=True)
        
        # Clean up whitespace
        lines = []
        for line in text.split("\n"):
            line = " ".join(line.split())
            if line:
                lines.append(line)
        
        return "\n".join(lines)
    
    def _extract_title(self, html: str) -> Optional[str]:
        """
        Extract page title from HTML.
        
        Args:
            html: Raw HTML content
            
        Returns:
            Page title or None
        """
        soup = BeautifulSoup(html, "lxml")
        
        # Try og:title first
        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            return og_title["content"]
        
        # Try title tag
        title_tag = soup.find("title")
        if title_tag:
            return title_tag.get_text(strip=True)
        
        # Try h1
        h1 = soup.find("h1")
        if h1:
            return h1.get_text(strip=True)
        
        return None
