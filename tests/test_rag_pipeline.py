"""Test RAG pipeline."""
import asyncio
import sys

sys.path.insert(0, "../")

from rag_server.config import RAGConfig
from rag_server.vector_db import QdrantVectorDB
from rag_server.embeddings import EmbeddingClient
from rag_server.llm_client import LLMClient
from rag_server.query_engine import RAGQueryEngine
from rag_server.models import IndexRequest, QueryRequest, Document


async def test_rag_pipeline():
    """Test full RAG pipeline."""
    print("Testing RAG Pipeline...")
    
    # Load config
    config = RAGConfig.from_env()
    config.qdrant_collection = "test_rag"
    
    # Initialize components
    vector_db = QdrantVectorDB(url=config.qdrant_url)
    embedding_client = EmbeddingClient(base_url=config.embedding_url)
    llm_client = LLMClient(base_url=config.llm_url)
    
    try:
        # Connect
        await vector_db.connect()
        print("✓ Connected to Qdrant")
        
        # Initialize query engine
        query_engine = RAGQueryEngine(
            config=config,
            vector_db=vector_db,
            embedding_client=embedding_client,
            llm_client=llm_client,
        )
        print("✓ Query engine initialized")
        
        # Clean up test collection if exists
        collections = await vector_db.list_collections()
        if config.qdrant_collection in collections:
            await vector_db.delete_collection(config.qdrant_collection)
            print("✓ Cleaned up test collection")
        
        # Index test documents
        test_docs = [
            Document(
                content="Python is a high-level programming language known for its simplicity and readability.",
                metadata={"source": "doc1.txt", "topic": "programming"}
            ),
            Document(
                content="Machine learning is a subset of artificial intelligence that enables systems to learn from data.",
                metadata={"source": "doc2.txt", "topic": "ai"}
            ),
            Document(
                content="FastAPI is a modern web framework for building APIs with Python, based on type hints.",
                metadata={"source": "doc3.txt", "topic": "web"}
            ),
        ]
        
        index_request = IndexRequest(documents=test_docs)
        index_response = await query_engine.index(index_request)
        print(f"✓ Indexed {index_response.indexed_count} documents")
        
        # Test search
        from rag_server.models import SearchRequest
        search_request = SearchRequest(
            query="What is Python?",
            limit=2
        )
        search_response = await query_engine.search(search_request)
        print(f"✓ Search found {len(search_response.results)} results")
        for idx, result in enumerate(search_response.results, 1):
            print(f"  [{idx}] Score: {result.score:.3f} - {result.content[:50]}...")
        
        # Test RAG query
        query_request = QueryRequest(
            query="Explain what Python is and why it's popular",
            limit=2,
            include_context=True
        )
        rag_response = await query_engine.query(query_request)
        print(f"\n✓ RAG Query completed")
        print(f"  Query: {rag_response.query}")
        print(f"  Sources: {len(rag_response.sources)}")
        print(f"  Answer: {rag_response.answer[:200]}...")
        
        # Cleanup
        await vector_db.delete_collection(config.qdrant_collection)
        print("\n✓ Cleaned up test collection")
        
        await vector_db.disconnect()
        await embedding_client.close()
        await llm_client.close()
        print("✓ Disconnected")
        
        print("\n✅ All RAG pipeline tests passed!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        
        await vector_db.disconnect()
        await embedding_client.close()
        await llm_client.close()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(test_rag_pipeline())
