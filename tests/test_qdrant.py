"""Test Qdrant connection."""
import asyncio
import sys

sys.path.insert(0, "../")

from rag_server.vector_db import QdrantVectorDB


async def test_qdrant():
    """Test Qdrant connection and basic operations."""
    print("Testing Qdrant connection...")
    
    # Initialize client
    client = QdrantVectorDB(url="http://localhost:6333")
    
    try:
        # Connect
        await client.connect()
        print("✓ Connected to Qdrant")
        
        # List collections
        collections = await client.list_collections()
        print(f"✓ Found {len(collections)} collections: {collections}")
        
        # Create test collection
        test_collection = "test_collection"
        if test_collection in collections:
            await client.delete_collection(test_collection)
            print(f"✓ Deleted existing collection '{test_collection}'")
        
        await client.create_collection(
            collection_name=test_collection,
            vector_size=768,
            distance="Cosine"
        )
        print(f"✓ Created collection '{test_collection}'")
        
        # Insert test document
        test_docs = [
            {
                "id": "test_1",
                "content": "This is a test document",
                "embedding": [0.1] * 768,  # Dummy embedding
                "metadata": {"source": "test"},
            }
        ]
        
        inserted_ids = await client.insert(test_collection, test_docs)
        print(f"✓ Inserted {len(inserted_ids)} documents")
        
        # Search
        results = await client.search(
            collection_name=test_collection,
            query_vector=[0.1] * 768,
            limit=5
        )
        print(f"✓ Search returned {len(results)} results")
        
        # Get collection info
        info = await client.get_collection_info(test_collection)
        print(f"✓ Collection info: {info}")
        
        # Cleanup
        await client.delete_collection(test_collection)
        print(f"✓ Deleted test collection")
        
        await client.disconnect()
        print("✓ Disconnected")
        
        print("\n✅ All tests passed!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        await client.disconnect()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(test_qdrant())
