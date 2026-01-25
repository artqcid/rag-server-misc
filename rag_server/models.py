"""Pydantic models for RAG server."""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class Document(BaseModel):
    """Document to be indexed."""
    
    id: Optional[str] = Field(
        default=None,
        description="Document ID (auto-generated if not provided)"
    )
    content: str = Field(
        ...,
        description="Document text content"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Document metadata"
    )


class IndexRequest(BaseModel):
    """Request to index documents."""
    
    documents: List[Document] = Field(
        ...,
        description="Documents to index"
    )
    collection: Optional[str] = Field(
        default=None,
        description="Collection name (uses default if not specified)"
    )


class IndexResponse(BaseModel):
    """Response from indexing operation."""
    
    indexed_count: int = Field(
        ...,
        description="Number of documents indexed"
    )
    document_ids: List[str] = Field(
        ...,
        description="IDs of indexed documents"
    )
    collection: str = Field(
        ...,
        description="Collection name"
    )


class QueryRequest(BaseModel):
    """Request for RAG query (retrieve + generate)."""
    
    query: str = Field(
        ...,
        description="Query text"
    )
    limit: int = Field(
        default=5,
        description="Number of documents to retrieve"
    )
    collection: Optional[str] = Field(
        default=None,
        description="Collection name"
    )
    include_context: bool = Field(
        default=True,
        description="Include retrieved context in response"
    )
    max_tokens: Optional[int] = Field(
        default=None,
        description="Max tokens for LLM response"
    )
    temperature: Optional[float] = Field(
        default=None,
        description="LLM temperature"
    )


class SearchRequest(BaseModel):
    """Request for vector search only (no LLM)."""
    
    query: str = Field(
        ...,
        description="Search query"
    )
    limit: int = Field(
        default=5,
        description="Number of results"
    )
    collection: Optional[str] = Field(
        default=None,
        description="Collection name"
    )
    min_score: Optional[float] = Field(
        default=None,
        description="Minimum similarity score"
    )


class SearchResult(BaseModel):
    """Single search result."""
    
    id: str = Field(
        ...,
        description="Document ID"
    )
    content: str = Field(
        ...,
        description="Document content"
    )
    metadata: Dict[str, Any] = Field(
        ...,
        description="Document metadata"
    )
    score: float = Field(
        ...,
        description="Similarity score (0-1)"
    )


class SearchResponse(BaseModel):
    """Response from search operation."""
    
    results: List[SearchResult] = Field(
        ...,
        description="Search results"
    )
    query: str = Field(
        ...,
        description="Original query"
    )
    collection: str = Field(
        ...,
        description="Collection name"
    )


class RAGResponse(BaseModel):
    """Response from RAG query (retrieve + generate)."""
    
    answer: str = Field(
        ...,
        description="Generated answer from LLM"
    )
    sources: List[SearchResult] = Field(
        ...,
        description="Retrieved source documents"
    )
    query: str = Field(
        ...,
        description="Original query"
    )
    context: Optional[str] = Field(
        default=None,
        description="Combined context sent to LLM"
    )
    collection: str = Field(
        ...,
        description="Collection name"
    )


class DeleteResponse(BaseModel):
    """Response from delete operation."""
    
    deleted: bool = Field(
        ...,
        description="Whether deletion was successful"
    )
    document_id: str = Field(
        ...,
        description="Deleted document ID"
    )


class HealthResponse(BaseModel):
    """Health check response."""
    
    status: str = Field(
        ...,
        description="Overall status"
    )
    qdrant: Dict[str, Any] = Field(
        ...,
        description="Qdrant connection status"
    )
    embedding: Dict[str, Any] = Field(
        ...,
        description="Embedding server status"
    )
    llm: Dict[str, Any] = Field(
        ...,
        description="LLM server status"
    )
    collections: List[str] = Field(
        ...,
        description="Available collections"
    )
