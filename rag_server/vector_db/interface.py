"""Vector database interface."""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional


class VectorDBInterface(ABC):
    """Abstract base class for vector databases."""

    @abstractmethod
    async def connect(self) -> None:
        """Connect to the vector database."""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the vector database."""
        pass

    @abstractmethod
    async def create_collection(
        self,
        collection_name: str,
        vector_size: int,
        distance: str = "Cosine"
    ) -> bool:
        """
        Create a new collection.
        
        Args:
            collection_name: Name of the collection
            vector_size: Size of the embedding vectors
            distance: Distance metric (Cosine, Dot, Euclid)
            
        Returns:
            True if created successfully
        """
        pass

    @abstractmethod
    async def collection_exists(self, collection_name: str) -> bool:
        """Check if a collection exists."""
        pass

    @abstractmethod
    async def list_collections(self) -> List[str]:
        """List all available collections."""
        pass

    @abstractmethod
    async def insert(
        self,
        collection_name: str,
        documents: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Insert documents with embeddings into collection.
        
        Args:
            collection_name: Name of the collection
            documents: List of documents with structure:
                {
                    "id": "doc_id",
                    "content": "text content",
                    "embedding": [0.1, 0.2, ...],
                    "metadata": {"key": "value"}
                }
                
        Returns:
            List of inserted document IDs
        """
        pass

    @abstractmethod
    async def search(
        self,
        collection_name: str,
        query_vector: List[float],
        limit: int = 5,
        min_score: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar vectors.
        
        Args:
            collection_name: Name of the collection
            query_vector: Query embedding vector
            limit: Maximum number of results
            min_score: Minimum similarity score (optional)
            
        Returns:
            List of results with structure:
                {
                    "id": "doc_id",
                    "content": "text",
                    "metadata": {...},
                    "score": 0.95
                }
        """
        pass

    @abstractmethod
    async def delete(
        self,
        collection_name: str,
        document_ids: List[str]
    ) -> bool:
        """
        Delete documents by IDs.
        
        Args:
            collection_name: Name of the collection
            document_ids: List of document IDs to delete
            
        Returns:
            True if deletion was successful
        """
        pass

    @abstractmethod
    async def delete_collection(self, collection_name: str) -> bool:
        """Delete an entire collection."""
        pass

    @abstractmethod
    async def get_collection_info(self, collection_name: str) -> Dict[str, Any]:
        """Get information about a collection."""
        pass
