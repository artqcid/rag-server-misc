"""Embedding server client."""
from typing import List
import httpx
import asyncio


class EmbeddingClient:
    """Client for embedding server (embedding-server-misc)."""

    def __init__(self, base_url: str = "http://127.0.0.1:8001", model: str = "nomic-embed-text-v1.5"):
        """
        Initialize embedding client.
        
        Args:
            base_url: Base URL of embedding server
            model: Model name
        """
        self.base_url = base_url.rstrip("/")
        self.model = model
        # Increased timeout for large batches
        self.client = httpx.AsyncClient(timeout=120.0, http2=False)
        self.max_retries = 3
        self.retry_delay = 2.0

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()

    async def embed(self, text: str) -> List[float]:
        """
        Get embedding for a single text.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector
        """
        embeddings = await self.embed_batch([text])
        return embeddings[0] if embeddings else []

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Get embeddings for multiple texts.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        if not texts:
            return []

        # Handle both base URL and full endpoint URL
        if "/v1/embeddings" in self.base_url:
            url = self.base_url
        else:
            url = f"{self.base_url}/v1/embeddings"
        payload = {
            "input": texts,
            "model": self.model,
        }

        try:
            # Retry logic for resilience
            last_error = None
            for attempt in range(self.max_retries):
                try:
                    response = await self.client.post(url, json=payload)
                    response.raise_for_status()
                    
                    data = response.json()
                    
                    # Extract embeddings from response
                    # Format: {"data": [{"embedding": [...]}, ...]}
                    embeddings = []
                    for item in data.get("data", []):
                        embeddings.append(item["embedding"])
                    
                    return embeddings
                    
                except (httpx.HTTPError, httpx.TimeoutException) as e:
                    last_error = e
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(self.retry_delay * (attempt + 1))
                        continue
                    raise
            
            raise RuntimeError(f"Embedding server error after {self.max_retries} retries: {last_error}")
            
        except httpx.HTTPError as e:
            raise RuntimeError(f"Embedding server error: {e}")

    async def health_check(self) -> bool:
        """Check if embedding server is healthy."""
        try:
            # Strip /v1/embeddings from base_url to get root health endpoint
            health_url = self.base_url.replace("/v1/embeddings", "")
            response = await self.client.get(f"{health_url}/health")
            return response.status_code == 200
        except Exception:
            return False
