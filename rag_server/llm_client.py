"""LLM server client."""
from typing import List, Dict, Any, Optional
import httpx


class LLMClient:
    """Client for LLM server (llama.cpp)."""

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8080",
        model: str = "qwen2.5-coder-7b",
        max_tokens: int = 2048,
        temperature: float = 0.7,
    ):
        """
        Initialize LLM client.
        
        Args:
            base_url: Base URL of LLM server
            model: Model name
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature
        """
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.client = httpx.AsyncClient(timeout=120.0, http2=False)

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()

    async def chat(
        self,
        messages: List[Dict[str, str]],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> str:
        """
        Send chat completion request.
        
        Args:
            messages: List of messages [{"role": "user", "content": "..."}]
            max_tokens: Override max_tokens
            temperature: Override temperature
            
        Returns:
            Generated text response
        """
        # Handle both base URL and full endpoint URL
        if "/v1/chat/completions" in self.base_url:
            url = self.base_url
        else:
            url = f"{self.base_url}/v1/chat/completions"
        
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens or self.max_tokens,
            "temperature": temperature if temperature is not None else self.temperature,
            "stream": False,
        }

        try:
            response = await self.client.post(url, json=payload)
            response.raise_for_status()
            
            data = response.json()
            
            # Extract content from response
            # Format: {"choices": [{"message": {"content": "..."}}]}
            if data.get("choices") and len(data["choices"]) > 0:
                return data["choices"][0]["message"]["content"]
            
            return ""
            
        except httpx.HTTPError as e:
            raise RuntimeError(f"LLM server error: {e}")

    async def generate_with_context(
        self,
        query: str,
        context: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> str:
        """
        Generate response with context (RAG pattern).
        
        Args:
            query: User query
            context: Retrieved context documents
            system_prompt: Custom system prompt (optional)
            max_tokens: Override max_tokens
            temperature: Override temperature
            
        Returns:
            Generated answer
        """
        # Default system prompt for RAG
        if not system_prompt:
            system_prompt = (
                "You are a helpful assistant. Answer the user's question based on the provided context. "
                "If the context doesn't contain enough information, say so honestly."
            )

        # Build user message with context
        user_message = f"""Context:
{context}

Question: {query}

Answer:"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]

        return await self.chat(messages, max_tokens, temperature)

    async def health_check(self) -> bool:
        """Check if LLM server is healthy."""
        try:
            response = await self.client.get(f"{self.base_url}/health")
            return response.status_code == 200
        except Exception:
            return False
