"""RAG query engine - orchestrates retrieval and generation."""
from typing import List, Dict, Any, Optional
import uuid

from .config import RAGConfig
from .vector_db import VectorDBInterface
from .embeddings import EmbeddingClient
from .llm_client import LLMClient
from .chunking import HybridChunker
from .models import (
    Document,
    IndexRequest,
    IndexResponse,
    QueryRequest,
    SearchRequest,
    RAGResponse,
    SearchResponse,
    SearchResult,
)


class RAGQueryEngine:
    """RAG Query Engine - handles indexing, retrieval, and generation."""

    def __init__(
        self,
        config: RAGConfig,
        vector_db: VectorDBInterface,
        embedding_client: EmbeddingClient,
        llm_client: LLMClient,
    ):
        """
        Initialize RAG query engine.
        
        Args:
            config: RAG configuration
            vector_db: Vector database client
            embedding_client: Embedding server client
            llm_client: LLM server client
        """
        self.config = config
        self.vector_db = vector_db
        self.embedding_client = embedding_client
        self.llm_client = llm_client
        
        # Initialize chunker
        self.chunker = HybridChunker(
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap,
            min_chunk_size=config.min_chunk_size,
            use_sentence_splitting=config.use_sentence_splitting,
        )

    async def ensure_collection(self, collection_name: str) -> None:
        """Ensure collection exists, create if not."""
        if not await self.vector_db.collection_exists(collection_name):
            await self.vector_db.create_collection(
                collection_name=collection_name,
                vector_size=self.config.embedding_dimensions,
                distance="Cosine",
            )

    async def index(self, request: IndexRequest) -> IndexResponse:
        """
        Index documents into vector database.
        
        Args:
            request: Index request with documents
            
        Returns:
            Index response with document IDs
        """
        collection_name = request.collection or self.config.qdrant_collection
        
        # Ensure collection exists
        await self.ensure_collection(collection_name)

        # Process each document
        all_chunks = []
        for doc in request.documents:
            # Chunk the document
            chunks_with_meta = self.chunker.chunk_with_metadata(
                text=doc.content,
                base_metadata={
                    "source_doc_id": doc.id or str(uuid.uuid4()),
                    **doc.metadata,
                }
            )
            all_chunks.extend(chunks_with_meta)

        # Get embeddings for all chunks
        chunk_texts = [chunk["content"] for chunk in all_chunks]
        embeddings = await self.embedding_client.embed_batch(chunk_texts)

        # Prepare documents for insertion
        documents_to_insert = []
        for chunk, embedding in zip(all_chunks, embeddings):
            documents_to_insert.append({
                "id": str(uuid.uuid4()),
                "content": chunk["content"],
                "embedding": embedding,
                "metadata": chunk["metadata"],
            })

        # Insert into vector database
        inserted_ids = await self.vector_db.insert(
            collection_name=collection_name,
            documents=documents_to_insert,
        )

        return IndexResponse(
            indexed_count=len(inserted_ids),
            document_ids=inserted_ids,
            collection=collection_name,
        )

    async def search(self, request: SearchRequest) -> SearchResponse:
        """
        Search for similar documents (retrieval only).
        
        Args:
            request: Search request
            
        Returns:
            Search response with results
        """
        collection_name = request.collection or self.config.qdrant_collection
        
        # Ensure collection exists
        await self.ensure_collection(collection_name)

        # Get query embedding
        query_embedding = await self.embedding_client.embed(request.query)

        # Search in vector database
        min_score = request.min_score or self.config.similarity_threshold
        results = await self.vector_db.search(
            collection_name=collection_name,
            query_vector=query_embedding,
            limit=request.limit,
            min_score=min_score,
        )

        # Format results
        search_results = [
            SearchResult(
                id=result["id"],
                content=result["content"],
                metadata=result["metadata"],
                score=result["score"],
            )
            for result in results
        ]

        return SearchResponse(
            results=search_results,
            query=request.query,
            collection=collection_name,
        )

    async def query(self, request: QueryRequest) -> RAGResponse:
        """
        RAG query - retrieve relevant documents and generate answer.
        
        Args:
            request: Query request
            
        Returns:
            RAG response with answer and sources
        """
        collection_name = request.collection or self.config.qdrant_collection
        
        # Ensure collection exists
        await self.ensure_collection(collection_name)

        # Get query embedding
        query_embedding = await self.embedding_client.embed(request.query)

        # Search in vector database
        results = await self.vector_db.search(
            collection_name=collection_name,
            query_vector=query_embedding,
            limit=request.limit,
            min_score=self.config.similarity_threshold,
        )

        # Format search results
        search_results = [
            SearchResult(
                id=result["id"],
                content=result["content"],
                metadata=result["metadata"],
                score=result["score"],
            )
            for result in results
        ]

        # Build context from retrieved documents
        context = self._build_context(search_results)

        # Generate answer using LLM
        max_tokens = request.max_tokens or self.config.llm_max_tokens
        temperature = request.temperature if request.temperature is not None else self.config.llm_temperature
        
        answer = await self.llm_client.generate_with_context(
            query=request.query,
            context=context,
            max_tokens=max_tokens,
            temperature=temperature,
        )

        return RAGResponse(
            answer=answer,
            sources=search_results,
            query=request.query,
            context=context if request.include_context else None,
            collection=collection_name,
        )

    def _build_context(self, results: List[SearchResult]) -> str:
        """
        Build context string from search results.
        
        Args:
            results: Search results
            
        Returns:
            Formatted context string
        """
        if not results:
            return "No relevant context found."

        context_parts = []
        for idx, result in enumerate(results, 1):
            source_info = ""
            if result.metadata:
                source = result.metadata.get("source", "")
                if source:
                    source_info = f" (Source: {source})"
            
            context_parts.append(
                f"[{idx}]{source_info} {result.content}"
            )

        return "\n\n".join(context_parts)

    async def delete_document(self, collection_name: str, document_id: str) -> bool:
        """
        Delete a document from collection.
        
        Args:
            collection_name: Collection name
            document_id: Document ID
            
        Returns:
            True if deleted successfully
        """
        return await self.vector_db.delete(
            collection_name=collection_name,
            document_ids=[document_id],
        )
