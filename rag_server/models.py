"""Pydantic models for RAG server."""
from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field
from datetime import datetime


# =============================================================================
# Document Metadata Schema (nach ChatGPT-Analyse)
# =============================================================================

class DocumentMetadata(BaseModel):
    """
    Strukturierte Metadaten für Dokumente.
    
    Pflichtfelder werden von Flowise/Ingestion Layer geliefert.
    Chunk-Felder werden vom RAG Server gesetzt.
    Semantische Felder sind optional für erweiterte Filterung.
    """
    
    # === Pflichtfelder (Ingestion Layer liefert) ===
    source: Literal["web", "file", "api", "manual"] = Field(
        default="manual",
        description="Quelle des Dokuments"
    )
    url: Optional[str] = Field(
        default=None,
        description="Original-URL des Dokuments"
    )
    title: Optional[str] = Field(
        default=None,
        description="Titel des Dokuments"
    )
    language: str = Field(
        default="en",
        description="Sprache des Dokuments (ISO 639-1)"
    )
    version: Optional[str] = Field(
        default=None,
        description="Version der Dokumentation (z.B. 'master', 'v1.0')"
    )
    ingestion_source: Optional[str] = Field(
        default=None,
        description="Tool das die Ingestion durchgeführt hat (flowise, n8n, cli)"
    )
    ingested_at: Optional[datetime] = Field(
        default=None,
        description="Zeitpunkt der Ingestion (automatisch gesetzt)"
    )
    
    # === Semantische Felder (optional, für erweiterte Filterung) ===
    doc_type: Optional[str] = Field(
        default=None,
        description="Typ: api_reference, tutorial, guide, etc."
    )
    library: Optional[str] = Field(
        default=None,
        description="Name der Library (JUCE, React, etc.)"
    )
    module: Optional[str] = Field(
        default=None,
        description="Modul-Name (audio_processors, gui_basics, etc.)"
    )
    symbol: Optional[str] = Field(
        default=None,
        description="Symbol-Name (Klasse, Funktion, etc.)"
    )
    symbol_type: Optional[str] = Field(
        default=None,
        description="Symbol-Typ: class, function, method, variable, etc."
    )
    
    # === Chunk-spezifische Felder (RAG Server setzt) ===
    chunk_index: Optional[int] = Field(
        default=None,
        description="Index des Chunks im Dokument (0-basiert)"
    )
    chunk_char_start: Optional[int] = Field(
        default=None,
        description="Startposition im Original-Text (Zeichen)"
    )
    chunk_char_end: Optional[int] = Field(
        default=None,
        description="Endposition im Original-Text (Zeichen)"
    )
    chunk_size: Optional[int] = Field(
        default=None,
        description="Größe des Chunks in Zeichen"
    )
    chunk_overlap: Optional[int] = Field(
        default=None,
        description="Überlappung mit vorherigem Chunk"
    )
    chunk_strategy: Optional[str] = Field(
        default=None,
        description="Verwendete Chunking-Strategie (sentence+char, fixed)"
    )
    total_chunks: Optional[int] = Field(
        default=None,
        description="Gesamtanzahl Chunks im Dokument"
    )
    source_doc_id: Optional[str] = Field(
        default=None,
        description="ID des Ursprungsdokuments"
    )
    
    class Config:
        extra = "allow"  # Erlaube zusätzliche Felder für Flexibilität


class Document(BaseModel):
    """Document to be indexed."""
    
    id: Optional[str] = Field(
        default=None,
        description="Document ID (auto-generated if not provided). Format: library:module:symbol"
    )
    content: str = Field(
        ...,
        description="Document text content (raw, wird vom RAG Server gechunked)"
    )
    metadata: DocumentMetadata = Field(
        default_factory=DocumentMetadata,
        description="Strukturierte Dokument-Metadaten"
    )


class LegacyDocument(BaseModel):
    """Legacy document format for backwards compatibility."""
    
    id: Optional[str] = Field(default=None)
    content: str = Field(...)
    metadata: Dict[str, Any] = Field(default_factory=dict)


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
