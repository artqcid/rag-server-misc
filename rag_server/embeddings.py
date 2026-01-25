"""Embedding server client."""
from typing import List
import httpx


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
        self.client = httpx.AsyncClient(timeout=30.0)

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

        url = f"{self.base_url}/v1/embeddings"
        payload = {
            "input": texts,
            "model": self.model,
        }

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
            
        except httpx.HTTPError as e:
            raise RuntimeError(f"Embedding server error: {e}")

    async def health_check(self) -> bool:
        """Check if embedding server is healthy."""
        try:
            response = await self.client.get(f"{self.base_url}/health")
            return response.status_code == 200
        except Exception:
            return False
