"""GitHub raw content fetching."""
import asyncio
import logging
from typing import Optional
import httpx

from .models import FetchResult, IndexingConfig

logger = logging.getLogger(__name__)


class GitHubFetcher:
    """Fetcher for raw GitHub content (headers, source files)."""
    
    def __init__(self, config: Optional[IndexingConfig] = None):
        """
        Initialize GitHub fetcher.
        
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
                    "Accept": "text/plain,application/octet-stream,*/*",
                }
            )
    
    async def close(self):
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def fetch(self, url: str, metadata: Optional[dict] = None) -> FetchResult:
        """
        Fetch raw content from GitHub.
        
        Args:
            url: GitHub raw URL to fetch
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
                response.raise_for_status()
                
                content = response.text
                
                # Truncate if too long
                if len(content) > self.config.max_content_length:
                    content = content[:self.config.max_content_length] + "\n\n/* Content truncated */"
                
                # Extract file info from URL
                file_info = self._extract_file_info(url)
                
                result_metadata = {
                    **metadata,
                    "url": url,
                    "source": "github",
                    **file_info,
                }
                
                return FetchResult(
                    url=url,
                    success=True,
                    content=content,
                    content_type="text/plain",
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
        
        return FetchResult(
            url=url,
            success=False,
            error="Max retries exceeded",
            metadata=metadata,
        )
    
    def _extract_file_info(self, url: str) -> dict:
        """
        Extract file information from GitHub URL.
        
        Args:
            url: GitHub raw URL
            
        Returns:
            Dict with file_name, file_extension, etc.
        """
        info = {}
        
        # Extract filename from URL
        if "/" in url:
            path = url.split("/")[-1]
            info["file_name"] = path
            
            if "." in path:
                info["file_extension"] = path.split(".")[-1]
        
        # Check if it's a raw.githubusercontent URL
        if "raw.githubusercontent.com" in url:
            parts = url.replace("https://raw.githubusercontent.com/", "").split("/")
            if len(parts) >= 3:
                info["github_owner"] = parts[0]
                info["github_repo"] = parts[1]
                info["github_branch"] = parts[2]
        
        return info
