"""Pydantic models for the indexing package."""
from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field
from datetime import datetime


class TierConfig(BaseModel):
    """Configuration for a single indexing tier."""
    
    description: str = Field(
        ...,
        description="Human-readable description of this tier"
    )
    source_type: Literal["web", "github", "file"] = Field(
        default="web",
        description="Type of content source"
    )
    doc_type: str = Field(
        ...,
        description="Document type for metadata (overview, class-reference, tutorial, header, etc.)"
    )
    urls: Optional[List[str]] = Field(
        default=None,
        description="Direct list of URLs to fetch"
    )
    url_pattern: Optional[str] = Field(
        default=None,
        description="URL pattern with placeholders for items"
    )
    items: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="List of items to substitute into url_pattern"
    )
    
    def get_urls(self) -> List[Dict[str, Any]]:
        """
        Generate list of URLs with their metadata.
        
        Returns:
            List of dicts with 'url' and 'metadata' keys
        """
        results = []
        
        if self.urls:
            # Direct URL list
            for url in self.urls:
                results.append({
                    "url": url,
                    "metadata": {
                        "doc_type": self.doc_type,
                        "source_type": self.source_type,
                    }
                })
        elif self.url_pattern and self.items:
            # Pattern-based URLs
            for item in self.items:
                url = self.url_pattern.format(**item)
                metadata = {
                    "doc_type": self.doc_type,
                    "source_type": self.source_type,
                    **{k: v for k, v in item.items() if k not in ["doc", "path"]}
                }
                results.append({
                    "url": url,
                    "metadata": metadata
                })
        
        return results


class ContextConfig(BaseModel):
    """Configuration for a complete indexing context (e.g., JUCE, Vue, React)."""
    
    context: str = Field(
        ...,
        description="Context identifier (lowercase, no spaces)"
    )
    library: str = Field(
        ...,
        description="Display name of the library/framework"
    )
    description: Optional[str] = Field(
        default=None,
        description="Human-readable description"
    )
    collection: Optional[str] = Field(
        default=None,
        description="Qdrant collection name (defaults to context name)"
    )
    tiers: Dict[str, TierConfig] = Field(
        ...,
        description="Tier configurations keyed by tier name"
    )
    
    def get_collection_name(self) -> str:
        """Get the Qdrant collection name for this context."""
        return self.collection or f"{self.context}-docs"
    
    def get_tier_names(self) -> List[str]:
        """Get sorted list of tier names."""
        return sorted(self.tiers.keys())
    
    def get_tier(self, tier_name: str) -> Optional[TierConfig]:
        """Get a specific tier configuration."""
        return self.tiers.get(tier_name)


class FetchResult(BaseModel):
    """Result of fetching a single URL."""
    
    url: str
    success: bool
    content: Optional[str] = None
    content_type: Optional[str] = None
    status_code: Optional[int] = None
    error: Optional[str] = None
    fetch_time: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ProcessedDocument(BaseModel):
    """A processed document ready for indexing."""
    
    content: str = Field(
        ...,
        description="Cleaned text content"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Document metadata"
    )
    url: str = Field(
        ...,
        description="Source URL"
    )
    title: Optional[str] = Field(
        default=None,
        description="Extracted or provided title"
    )
    char_count: int = Field(
        default=0,
        description="Character count of content"
    )


class IndexingResult(BaseModel):
    """Result of an indexing operation."""
    
    context: str
    tier: str
    collection: str
    total_urls: int = 0
    successful_fetches: int = 0
    failed_fetches: int = 0
    documents_indexed: int = 0
    chunks_created: int = 0
    errors: List[str] = Field(default_factory=list)
    duration_seconds: float = 0.0
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    def summary(self) -> str:
        """Generate a summary string."""
        return (
            f"Indexed {self.context}/{self.tier}: "
            f"{self.successful_fetches}/{self.total_urls} URLs fetched, "
            f"{self.documents_indexed} docs, {self.chunks_created} chunks "
            f"in {self.duration_seconds:.1f}s"
        )


class IndexingConfig(BaseModel):
    """Global indexing configuration."""
    
    batch_size: int = Field(
        default=10,
        description="Documents per batch for indexing"
    )
    request_delay: float = Field(
        default=0.5,
        description="Delay between HTTP requests (rate limiting)"
    )
    max_content_length: int = Field(
        default=50000,
        description="Maximum characters per document"
    )
    request_timeout: float = Field(
        default=30.0,
        description="HTTP request timeout in seconds"
    )
    max_retries: int = Field(
        default=3,
        description="Maximum retry attempts for failed requests"
    )
    user_agent: str = Field(
        default="RAG-Indexer/1.0 (Python)",
        description="User agent for HTTP requests"
    )
