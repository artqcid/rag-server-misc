"""Qdrant vector database client implementation with hybrid search support."""
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    SparseVectorParams,
    SparseIndexParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
    NamedVector,
    NamedSparseVector,
    SparseVector,
    Prefetch,
    FusionQuery,
    Fusion,
)
from qdrant_client.http.exceptions import UnexpectedResponse
import uuid

from .interface import VectorDBInterface
from ..sparse_encoder import BM25SparseEncoder, get_sparse_encoder


class QdrantVectorDB(VectorDBInterface):
    """Qdrant vector database implementation with hybrid search support."""

    # Named vector keys for hybrid search
    DENSE_VECTOR_NAME = "dense"
    SPARSE_VECTOR_NAME = "sparse"

    def __init__(
        self,
        url: str = "http://localhost:6333",
        api_key: Optional[str] = None,
        enable_hybrid: bool = True,
        sparse_vocab_size: int = 30000,
    ):
        """
        Initialize Qdrant client.
        
        Args:
            url: Qdrant server URL
            api_key: API key for Qdrant Cloud (optional)
            enable_hybrid: Enable hybrid search with sparse vectors
            sparse_vocab_size: Vocabulary size for BM25 sparse encoder
        """
        self.url = url
        self.api_key = api_key
        self.client: Optional[QdrantClient] = None
        self.enable_hybrid = enable_hybrid
        self.sparse_encoder = BM25SparseEncoder(vocab_size=sparse_vocab_size) if enable_hybrid else None

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
        """Create a new collection in Qdrant with optional hybrid search support."""
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
            if self.enable_hybrid:
                # Create collection with named vectors for hybrid search
                self.client.create_collection(
                    collection_name=collection_name,
                    vectors_config={
                        self.DENSE_VECTOR_NAME: VectorParams(
                            size=vector_size,
                            distance=distance_metric,
                        ),
                    },
                    sparse_vectors_config={
                        self.SPARSE_VECTOR_NAME: SparseVectorParams(
                            index=SparseIndexParams(
                                on_disk=False,
                            ),
                        ),
                    },
                )
            else:
                # Legacy: single unnamed vector
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

        # Check if collection supports hybrid search
        collection_is_hybrid = await self._collection_supports_hybrid(collection_name)

        points = []
        inserted_ids = []

        for doc in documents:
            # Generate ID if not provided
            doc_id = doc.get("id") or str(uuid.uuid4())
            inserted_ids.append(doc_id)

            content = doc["content"]
            payload = {
                "content": content,
                "metadata": doc.get("metadata", {}),
            }

            if self.enable_hybrid and collection_is_hybrid and self.sparse_encoder:
                # Hybrid mode: named vectors (dense + sparse)
                sparse_data = self.sparse_encoder.to_qdrant_sparse(content)
                
                point = PointStruct(
                    id=doc_id,
                    vector={
                        self.DENSE_VECTOR_NAME: doc["embedding"],
                    },
                    payload=payload,
                )
                # Add sparse vector separately
                point.vector[self.SPARSE_VECTOR_NAME] = SparseVector(
                    indices=sparse_data["indices"],
                    values=sparse_data["values"],
                )
            else:
                # Legacy mode: single unnamed vector
                point = PointStruct(
                    id=doc_id,
                    vector=doc["embedding"],
                    payload=payload,
                )
            points.append(point)

        # Upsert points (insert or update)
        self.client.upsert(
            collection_name=collection_name,
            points=points,
        )

        return inserted_ids

    async def _collection_supports_hybrid(self, collection_name: str) -> bool:
        """Check if collection has sparse vectors configured."""
        if not self.client:
            return False
        try:
            info = self.client.get_collection(collection_name)
            # Check if sparse_vectors_config exists and has our sparse vector
            sparse_config = info.config.params.sparse_vectors
            return sparse_config is not None and self.SPARSE_VECTOR_NAME in sparse_config
        except Exception:
            return False

    async def _collection_has_named_vectors(self, collection_name: str) -> bool:
        """Check if collection uses named vectors (hybrid) vs single unnamed vector."""
        if not self.client:
            return False
        try:
            info = self.client.get_collection(collection_name)
            vectors_config = info.config.params.vectors
            # If vectors_config is a dict, it uses named vectors
            return isinstance(vectors_config, dict)
        except Exception:
            return False

    async def search(
        self,
        collection_name: str,
        query_vector: List[float],
        limit: int = 5,
        min_score: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """Search for similar vectors in Qdrant (dense only, for legacy collections)."""
        if not self.client:
            raise RuntimeError("Client not connected.")

        # Check if collection uses named vectors
        has_named = await self._collection_has_named_vectors(collection_name)
        
        if has_named:
            # Named vectors: specify which vector to query
            results = self.client.query_points(
                collection_name=collection_name,
                query=query_vector,
                using=self.DENSE_VECTOR_NAME,
                limit=limit,
                score_threshold=min_score,
            ).points
        else:
            # Legacy: single unnamed vector
            results = self.client.query_points(
                collection_name=collection_name,
                query=query_vector,
                limit=limit,
                score_threshold=min_score,
            ).points

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

    async def hybrid_search(
        self,
        collection_name: str,
        query_vector: List[float],
        query_text: str,
        limit: int = 5,
        min_score: Optional[float] = None,
        dense_weight: float = 0.7,
        sparse_weight: float = 0.3,
    ) -> List[Dict[str, Any]]:
        """
        Hybrid search combining dense and sparse vectors with RRF fusion.
        
        Args:
            collection_name: Collection to search
            query_vector: Dense embedding vector
            query_text: Original query text for sparse encoding
            limit: Number of results
            min_score: Minimum score threshold
            dense_weight: Weight for dense vector results (0-1)
            sparse_weight: Weight for sparse vector results (0-1)
            
        Returns:
            List of search results with combined scores
        """
        if not self.client:
            raise RuntimeError("Client not connected.")

        # Check if collection supports hybrid
        supports_hybrid = await self._collection_supports_hybrid(collection_name)
        
        if not supports_hybrid or not self.sparse_encoder:
            # Fallback to dense-only search
            return await self.search(collection_name, query_vector, limit, min_score)

        # Encode query text to sparse vector
        sparse_data = self.sparse_encoder.to_qdrant_sparse(query_text)
        
        # Use Qdrant's built-in RRF fusion for hybrid search
        results = self.client.query_points(
            collection_name=collection_name,
            prefetch=[
                # Dense vector search
                Prefetch(
                    query=query_vector,
                    using=self.DENSE_VECTOR_NAME,
                    limit=limit * 2,  # Fetch more for better fusion
                ),
                # Sparse vector search
                Prefetch(
                    query=SparseVector(
                        indices=sparse_data["indices"],
                        values=sparse_data["values"],
                    ),
                    using=self.SPARSE_VECTOR_NAME,
                    limit=limit * 2,
                ),
            ],
            query=FusionQuery(fusion=Fusion.RRF),  # Reciprocal Rank Fusion
            limit=limit,
            score_threshold=min_score,
        ).points

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
            
            # Handle both named and unnamed vector configs
            vectors_config = info.config.params.vectors
            if isinstance(vectors_config, dict):
                # Named vectors (hybrid mode)
                dense_config = vectors_config.get(self.DENSE_VECTOR_NAME)
                vector_size = dense_config.size if dense_config else 0
                distance = dense_config.distance.name if dense_config else "unknown"
            else:
                # Single unnamed vector
                vector_size = vectors_config.size
                distance = vectors_config.distance.name
            
            return {
                "name": collection_name,
                "points_count": info.points_count,
                "status": str(info.status),
                "config": {
                    "vector_size": vector_size,
                    "distance": distance,
                },
                "hybrid_enabled": await self._collection_supports_hybrid(collection_name),
            }
        except Exception as e:
            raise ValueError(f"Error getting collection info: {e}")
