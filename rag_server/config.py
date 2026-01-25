"""Configuration for RAG Server."""
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field
import os


class RAGConfig(BaseSettings):
    """RAG Server configuration."""

    # Qdrant Configuration
    qdrant_url: str = Field(
        default="http://localhost:6333",
        description="Qdrant server URL"
    )
    qdrant_collection: str = Field(
        default="documents",
        description="Default collection name"
    )
    qdrant_api_key: Optional[str] = Field(
        default=None,
        description="Qdrant Cloud API key (optional)"
    )

    # Embedding Server Integration
    embedding_url: str = Field(
        default="http://127.0.0.1:8001/v1/embeddings",
        description="Embedding server endpoint"
    )
    embedding_model: str = Field(
        default="nomic-embed-text-v1.5",
        description="Embedding model name"
    )
    embedding_dimensions: int = Field(
        default=768,
        description="Embedding vector dimensions"
    )

    # LLM Server Integration
    llm_url: str = Field(
        default="http://127.0.0.1:8080/v1/chat/completions",
        description="LLM server endpoint"
    )
    llm_model: str = Field(
        default="qwen2.5-coder-7b",
        description="LLM model name"
    )
    llm_max_tokens: int = Field(
        default=2048,
        description="Max tokens for LLM response"
    )
    llm_temperature: float = Field(
        default=0.7,
        description="LLM temperature"
    )

    # RAG Parameters
    chunk_size: int = Field(
        default=512,
        description="Text chunk size in characters"
    )
    chunk_overlap: int = Field(
        default=50,
        description="Overlap between chunks"
    )
    retrieval_limit: int = Field(
        default=5,
        description="Number of documents to retrieve"
    )
    similarity_threshold: float = Field(
        default=0.7,
        description="Minimum similarity score (0-1)"
    )

    # Chunking Strategy
    use_sentence_splitting: bool = Field(
        default=True,
        description="Enable sentence-based splitting"
    )
    min_chunk_size: int = Field(
        default=100,
        description="Minimum chunk size"
    )

    # Server Configuration
    host: str = Field(
        default="127.0.0.1",
        description="Server host"
    )
    port: int = Field(
        default=8002,
        description="Server port"
    )
    verbose: bool = Field(
        default=False,
        description="Enable verbose logging"
    )

    @classmethod
    def from_env(cls) -> "RAGConfig":
        """Load config from environment variables."""
        return cls(
            # Qdrant
            qdrant_url=os.getenv("RAG_QDRANT_URL", "http://localhost:6333"),
            qdrant_collection=os.getenv("RAG_QDRANT_COLLECTION", "documents"),
            qdrant_api_key=os.getenv("RAG_QDRANT_API_KEY"),
            
            # Embedding
            embedding_url=os.getenv(
                "RAG_EMBEDDING_URL",
                "http://127.0.0.1:8001/v1/embeddings"
            ),
            embedding_model=os.getenv("RAG_EMBEDDING_MODEL", "nomic-embed-text-v1.5"),
            embedding_dimensions=int(os.getenv("RAG_EMBEDDING_DIM", "768")),
            
            # LLM
            llm_url=os.getenv(
                "RAG_LLM_URL",
                "http://127.0.0.1:8080/v1/chat/completions"
            ),
            llm_model=os.getenv("RAG_LLM_MODEL", "qwen2.5-coder-7b"),
            llm_max_tokens=int(os.getenv("RAG_LLM_MAX_TOKENS", "2048")),
            llm_temperature=float(os.getenv("RAG_LLM_TEMPERATURE", "0.7")),
            
            # RAG Parameters
            chunk_size=int(os.getenv("RAG_CHUNK_SIZE", "512")),
            chunk_overlap=int(os.getenv("RAG_CHUNK_OVERLAP", "50")),
            retrieval_limit=int(os.getenv("RAG_RETRIEVAL_LIMIT", "5")),
            similarity_threshold=float(os.getenv("RAG_SIMILARITY_THRESHOLD", "0.7")),
            
            # Chunking
            use_sentence_splitting=os.getenv(
                "RAG_USE_SENTENCE_SPLITTING", "true"
            ).lower() == "true",
            min_chunk_size=int(os.getenv("RAG_MIN_CHUNK_SIZE", "100")),
            
            # Server
            host=os.getenv("RAG_HOST", "127.0.0.1"),
            port=int(os.getenv("RAG_PORT", "8002")),
            verbose=os.getenv("RAG_VERBOSE", "").lower() == "true",
        )

    class Config:
        env_prefix = "RAG_"
        case_sensitive = False
