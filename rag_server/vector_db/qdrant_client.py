"""Qdrant vector database client implementation."""
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
)
from qdrant_client.http.exceptions import UnexpectedResponse
import uuid

from .interface import VectorDBInterface


class QdrantVectorDB(VectorDBInterface):
    """Qdrant vector database implementation."""

    def __init__(
        self,
        url: str = "http://localhost:6333",
        api_key: Optional[str] = None,
    ):
        """
        Initialize Qdrant client.
        
        Args:
            url: Qdrant server URL
            api_key: API key for Qdrant Cloud (optional)
        """
        self.url = url
        self.api_key = api_key
        self.client: Optional[QdrantClient] = None

    async def connect(self) -> None:
        """Connect to Qdrant server."""
        try:
            self.client = QdrantClient(
                url=self.url,
                api_key=self.api_key,
                timeout=10.0,
            )
            # Test connection
            self.client.get_collections()
        except Exception as e:
            raise ConnectionError(f"Failed to connect to Qdrant at {self.url}: {e}")

    async def disconnect(self) -> None:
        """Disconnect from Qdrant."""
        if self.client:
            self.client.close()
            self.client = None

    async def create_collection(
        self,
        collection_name: str,
        vector_size: int,
        distance: str = "Cosine"
    ) -> bool:
        """Create a new collection in Qdrant."""
        if not self.client:
            raise RuntimeError("Client not connected. Call connect() first.")

        # Map distance metric
        distance_map = {
            "Cosine": Distance.COSINE,
            "Dot": Distance.DOT,
            "Euclid": Distance.EUCLID,
            "Manhattan": Distance.MANHATTAN,
        }
        
        distance_metric = distance_map.get(distance, Distance.COSINE)

        try:
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=vector_size,
                    distance=distance_metric,
                ),
            )
            return True
        except UnexpectedResponse as e:
            if "already exists" in str(e).lower():
                return True  # Collection already exists
            raise

    async def collection_exists(self, collection_name: str) -> bool:
        """Check if a collection exists."""
        if not self.client:
            raise RuntimeError("Client not connected.")

        try:
            collections = self.client.get_collections().collections
            return any(c.name == collection_name for c in collections)
        except Exception:
            return False

    async def list_collections(self) -> List[str]:
        """List all collections."""
        if not self.client:
            raise RuntimeError("Client not connected.")

        collections = self.client.get_collections().collections
        return [c.name for c in collections]

    async def insert(
        self,
        collection_name: str,
        documents: List[Dict[str, Any]]
    ) -> List[str]:
        """Insert documents into Qdrant."""
        if not self.client:
            raise RuntimeError("Client not connected.")

        # Ensure collection exists
        if not await self.collection_exists(collection_name):
            raise ValueError(f"Collection '{collection_name}' does not exist")

        points = []
        inserted_ids = []

        for doc in documents:
            # Generate ID if not provided
            doc_id = doc.get("id") or str(uuid.uuid4())
            inserted_ids.append(doc_id)

            # Create point
            point = PointStruct(
                id=doc_id,
                vector=doc["embedding"],
                payload={
                    "content": doc["content"],
                    "metadata": doc.get("metadata", {}),
                },
            )
            points.append(point)

        # Upsert points (insert or update)
        self.client.upsert(
            collection_name=collection_name,
            points=points,
        )

        return inserted_ids

    async def search(
        self,
        collection_name: str,
        query_vector: List[float],
        limit: int = 5,
        min_score: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """Search for similar vectors in Qdrant."""
        if not self.client:
            raise RuntimeError("Client not connected.")

        # Perform search
        results = self.client.search(
            collection_name=collection_name,
            query_vector=query_vector,
            limit=limit,
            score_threshold=min_score,
        )

        # Format results
        formatted_results = []
        for hit in results:
            formatted_results.append({
                "id": str(hit.id),
                "content": hit.payload.get("content", ""),
                "metadata": hit.payload.get("metadata", {}),
                "score": float(hit.score),
            })

        return formatted_results

    async def delete(
        self,
        collection_name: str,
        document_ids: List[str]
    ) -> bool:
        """Delete documents from Qdrant."""
        if not self.client:
            raise RuntimeError("Client not connected.")

        try:
            self.client.delete(
                collection_name=collection_name,
                points_selector=document_ids,
            )
            return True
        except Exception as e:
            print(f"Error deleting documents: {e}")
            return False

    async def delete_collection(self, collection_name: str) -> bool:
        """Delete a collection."""
        if not self.client:
            raise RuntimeError("Client not connected.")

        try:
            self.client.delete_collection(collection_name=collection_name)
            return True
        except Exception as e:
            print(f"Error deleting collection: {e}")
            return False

    async def get_collection_info(self, collection_name: str) -> Dict[str, Any]:
        """Get collection information."""
        if not self.client:
            raise RuntimeError("Client not connected.")

        try:
            info = self.client.get_collection(collection_name=collection_name)
            return {
                "name": collection_name,
                "vectors_count": info.vectors_count,
                "points_count": info.points_count,
                "status": info.status,
                "config": {
                    "vector_size": info.config.params.vectors.size,
                    "distance": info.config.params.vectors.distance.name,
                },
            }
        except Exception as e:
            raise ValueError(f"Error getting collection info: {e}")
