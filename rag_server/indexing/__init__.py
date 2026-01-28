"""
RAG Server Indexing Package.

This package provides Python-based web content indexing for the RAG system,
replacing the n8n workflow approach with native Python implementations.

Features:
- Tier-based indexing (configurable URL groups)
- Web scraping with HTML parsing
- GitHub raw content fetching
- Context-based URL configuration
- CLI interface for VS Code task integration
"""
from .models import (
    TierConfig,
    ContextConfig,
    FetchResult,
    ProcessedDocument,
    IndexingResult,
)
from .url_sets import URLSetManager
from .tier_runner import TierRunner

__all__ = [
    "TierConfig",
    "ContextConfig",
    "FetchResult",
    "ProcessedDocument",
    "IndexingResult",
    "URLSetManager",
    "TierRunner",
]
