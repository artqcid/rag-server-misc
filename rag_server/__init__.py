"""RAG Server Package."""

__version__ = "1.0.0"
__author__ = "artqcid"

from .config import RAGConfig
from .models import (
    IndexRequest,
    QueryRequest,
    SearchRequest,
    RAGResponse,
    SearchResponse,
)

__all__ = [
    "RAGConfig",
    "IndexRequest",
    "QueryRequest",
    "SearchRequest",
    "RAGResponse",
    "SearchResponse",
]
