"""FastAPI server for RAG system."""
import logging
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

# Configure logging
logger = logging.getLogger(__name__)

from .config import RAGConfig
from .models import (
    IndexRequest,
    IndexResponse,
    QueryRequest,
    SearchRequest,
    RAGResponse,
    SearchResponse,
    DeleteResponse,
    HealthResponse,
)
from .query_engine import RAGQueryEngine
from .vector_db import QdrantVectorDB
from .embeddings import EmbeddingClient
from .llm_client import LLMClient


class RAGServer:
    """RAG Server with FastAPI."""

    def __init__(self, config: RAGConfig):
        """Initialize RAG server."""
        self.config = config
        self.vector_db: Optional[QdrantVectorDB] = None
        self.embedding_client: Optional[EmbeddingClient] = None
        self.llm_client: Optional[LLMClient] = None
        self.query_engine: Optional[RAGQueryEngine] = None

    async def startup(self):
        """Initialize connections on startup."""
        print("Starting RAG server...")
        
        # Initialize vector database with hybrid search support
        self.vector_db = QdrantVectorDB(
            url=self.config.qdrant_url,
            api_key=self.config.qdrant_api_key,
            enable_hybrid=self.config.enable_hybrid_search,
            sparse_vocab_size=self.config.sparse_vocab_size,
        )
        await self.vector_db.connect()
        hybrid_status = "enabled" if self.config.enable_hybrid_search else "disabled"
        print(f"✓ Connected to Qdrant at {self.config.qdrant_url} (hybrid search: {hybrid_status})")

        # Initialize embedding client
        self.embedding_client = EmbeddingClient(
            base_url=self.config.embedding_url,
            model=self.config.embedding_model,
        )
        print(f"✓ Connected to Embedding server at {self.config.embedding_url}")

        # Initialize LLM client
        self.llm_client = LLMClient(
            base_url=self.config.llm_url,
            model=self.config.llm_model,
            max_tokens=self.config.llm_max_tokens,
            temperature=self.config.llm_temperature,
        )
        print(f"✓ Connected to LLM server at {self.config.llm_url}")

        # Initialize query engine
        self.query_engine = RAGQueryEngine(
            config=self.config,
            vector_db=self.vector_db,
            embedding_client=self.embedding_client,
            llm_client=self.llm_client,
        )
        print("✓ RAG Query Engine initialized")

        # Ensure default collection exists
        await self.query_engine.ensure_collection(self.config.qdrant_collection)
        print(f"✓ Collection '{self.config.qdrant_collection}' ready")

    async def shutdown(self):
        """Clean up connections on shutdown."""
        print("Shutting down RAG server...")
        
        if self.vector_db:
            await self.vector_db.disconnect()
        if self.embedding_client:
            await self.embedding_client.close()
        if self.llm_client:
            await self.llm_client.close()
        
        print("✓ Shutdown complete")


def create_app(config: Optional[RAGConfig] = None) -> FastAPI:
    """
    Create FastAPI application.
    
    Args:
        config: RAG configuration (uses default if not provided)
        
    Returns:
        FastAPI application
    """
    if config is None:
        config = RAGConfig.from_env()

    # Create server instance
    server = RAGServer(config)

    # Lifespan context manager
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Startup
        await server.startup()
        yield
        # Shutdown
        await server.shutdown()

    # Create FastAPI app
    app = FastAPI(
        title="RAG Server",
        description="Retrieval-Augmented Generation server with Qdrant",
        version="1.0.0",
        lifespan=lifespan,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routes
    @app.post("/v1/rag/index", response_model=IndexResponse)
    async def index_documents(request: IndexRequest):
        """Index documents into vector database."""
        if not server.query_engine:
            raise HTTPException(500, "Query engine not initialized")
        
        doc_count = len(request.documents)
        logger.info(f"Indexing request received: {doc_count} documents")
        
        try:
            result = await server.query_engine.index(request)
            logger.info(f"Indexing complete: {result.indexed_count} chunks indexed")
            return result
        except Exception as e:
            logger.error(f"Indexing failed: {str(e)}", exc_info=True)
            raise HTTPException(500, f"Indexing failed: {str(e)}")

    @app.post("/v1/rag/query", response_model=RAGResponse)
    async def rag_query(request: QueryRequest):
        """RAG query - retrieve and generate answer."""
        if not server.query_engine:
            raise HTTPException(500, "Query engine not initialized")
        
        try:
            return await server.query_engine.query(request)
        except Exception as e:
            raise HTTPException(500, f"Query failed: {str(e)}")

    @app.post("/v1/rag/search", response_model=SearchResponse)
    async def search_documents(request: SearchRequest):
        """Search for similar documents (retrieval only)."""
        if not server.query_engine:
            raise HTTPException(500, "Query engine not initialized")
        
        try:
            return await server.query_engine.search(request)
        except Exception as e:
            raise HTTPException(500, f"Search failed: {str(e)}")

    @app.delete("/v1/rag/documents/{document_id}", response_model=DeleteResponse)
    async def delete_document(
        document_id: str,
        collection: Optional[str] = None
    ):
        """Delete a document by ID."""
        if not server.query_engine:
            raise HTTPException(500, "Query engine not initialized")
        
        collection_name = collection or config.qdrant_collection
        
        try:
            deleted = await server.query_engine.delete_document(
                collection_name=collection_name,
                document_id=document_id,
            )
            return DeleteResponse(deleted=deleted, document_id=document_id)
        except Exception as e:
            raise HTTPException(500, f"Delete failed: {str(e)}")

    @app.get("/health", response_model=HealthResponse)
    async def health_check():
        """Health check endpoint."""
        if not server.vector_db or not server.embedding_client or not server.llm_client:
            raise HTTPException(503, "Server not fully initialized")

        try:
            # Check Qdrant
            collections = await server.vector_db.list_collections()
            qdrant_status = {
                "connected": True,
                "url": config.qdrant_url,
                "collections": len(collections),
            }
        except Exception as e:
            qdrant_status = {
                "connected": False,
                "error": str(e),
            }

        try:
            # Check Embedding server
            embedding_healthy = await server.embedding_client.health_check()
            embedding_status = {
                "connected": embedding_healthy,
                "url": config.embedding_url,
            }
        except Exception as e:
            embedding_status = {
                "connected": False,
                "error": str(e),
            }

        try:
            # Check LLM server
            llm_healthy = await server.llm_client.health_check()
            llm_status = {
                "connected": llm_healthy,
                "url": config.llm_url,
            }
        except Exception as e:
            llm_status = {
                "connected": False,
                "error": str(e),
            }

        # Overall status
        all_healthy = (
            qdrant_status.get("connected", False) and
            embedding_status.get("connected", False) and
            llm_status.get("connected", False)
        )

        return HealthResponse(
            status="healthy" if all_healthy else "degraded",
            qdrant=qdrant_status,
            embedding=embedding_status,
            llm=llm_status,
            collections=collections if qdrant_status.get("connected") else [],
        )

    @app.get("/")
    async def root():
        """Root endpoint."""
        return {
            "name": "RAG Server",
            "version": "1.0.0",
            "status": "running",
            "endpoints": {
                "index": "/v1/rag/index",
                "query": "/v1/rag/query",
                "search": "/v1/rag/search",
                "delete": "/v1/rag/documents/{id}",
                "health": "/health",
            },
        }

    return app
