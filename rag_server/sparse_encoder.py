"""Sparse encoder for hybrid search using BM25."""
import math
import re
from collections import Counter
from typing import Dict, List, Tuple, Optional
import hashlib


class BM25SparseEncoder:
    """
    BM25-based sparse encoder for hybrid search.
    
    Converts text into sparse vectors using BM25 term weighting.
    Uses vocabulary hashing for fixed-dimension sparse vectors.
    """

    def __init__(
        self,
        vocab_size: int = 30000,
        k1: float = 1.5,
        b: float = 0.75,
        min_token_length: int = 2,
    ):
        """
        Initialize BM25 encoder.
        
        Args:
            vocab_size: Size of vocabulary (sparse vector dimension)
            k1: BM25 term frequency saturation parameter
            b: BM25 length normalization parameter
            min_token_length: Minimum token length to consider
        """
        self.vocab_size = vocab_size
        self.k1 = k1
        self.b = b
        self.min_token_length = min_token_length
        
        # IDF storage (can be updated with corpus statistics)
        self.idf: Dict[str, float] = {}
        self.avg_doc_length: float = 100.0  # Default average
        self.doc_count: int = 0

    def tokenize(self, text: str) -> List[str]:
        """
        Tokenize text into lowercase words.
        
        Args:
            text: Input text
            
        Returns:
            List of tokens
        """
        # Simple tokenization: lowercase, split on non-alphanumeric
        text = text.lower()
        tokens = re.findall(r'\b[a-z0-9_]+\b', text)
        
        # Filter by length
        tokens = [t for t in tokens if len(t) >= self.min_token_length]
        
        return tokens

    def _hash_token(self, token: str) -> int:
        """
        Hash token to vocabulary index.
        
        Args:
            token: Token string
            
        Returns:
            Index in [0, vocab_size)
        """
        # Use MD5 for consistent hashing
        hash_bytes = hashlib.md5(token.encode()).digest()
        hash_int = int.from_bytes(hash_bytes[:8], 'big')
        return hash_int % self.vocab_size

    def get_idf(self, token: str) -> float:
        """
        Get IDF score for token.
        
        Args:
            token: Token string
            
        Returns:
            IDF score (default 1.0 if not in corpus)
        """
        if token in self.idf:
            return self.idf[token]
        
        # Default IDF for unknown tokens (assume rare = high IDF)
        # log((N - n + 0.5) / (n + 0.5)) where n=1, N=large
        return math.log((self.doc_count + 1) / 1.5) if self.doc_count > 0 else 1.0

    def encode(self, text: str) -> Tuple[List[int], List[float]]:
        """
        Encode text to sparse vector (indices + values format).
        
        Args:
            text: Input text
            
        Returns:
            Tuple of (indices, values) for sparse vector
        """
        tokens = self.tokenize(text)
        
        if not tokens:
            return [], []
        
        # Count term frequencies
        tf_counts = Counter(tokens)
        doc_length = len(tokens)
        
        # Calculate BM25 weights
        indices_values: Dict[int, float] = {}
        
        for token, tf in tf_counts.items():
            # BM25 term weight
            idf = self.get_idf(token)
            
            # Length normalization
            length_norm = 1 - self.b + self.b * (doc_length / self.avg_doc_length)
            
            # BM25 TF component
            tf_weight = (tf * (self.k1 + 1)) / (tf + self.k1 * length_norm)
            
            # Final weight
            weight = idf * tf_weight
            
            # Hash to index
            idx = self._hash_token(token)
            
            # Aggregate if collision (sum weights)
            if idx in indices_values:
                indices_values[idx] += weight
            else:
                indices_values[idx] = weight
        
        # Sort by index for consistent ordering
        sorted_items = sorted(indices_values.items())
        indices = [item[0] for item in sorted_items]
        values = [item[1] for item in sorted_items]
        
        return indices, values

    def encode_batch(self, texts: List[str]) -> List[Tuple[List[int], List[float]]]:
        """
        Encode multiple texts.
        
        Args:
            texts: List of input texts
            
        Returns:
            List of (indices, values) tuples
        """
        return [self.encode(text) for text in texts]

    def update_idf_from_corpus(self, documents: List[str]) -> None:
        """
        Update IDF statistics from a corpus of documents.
        
        Args:
            documents: List of document texts
        """
        self.doc_count = len(documents)
        
        if self.doc_count == 0:
            return
        
        # Count document frequencies
        df: Dict[str, int] = Counter()
        total_length = 0
        
        for doc in documents:
            tokens = set(self.tokenize(doc))
            for token in tokens:
                df[token] += 1
            total_length += len(self.tokenize(doc))
        
        # Calculate IDF
        self.avg_doc_length = total_length / self.doc_count
        
        for token, doc_freq in df.items():
            # BM25 IDF formula
            self.idf[token] = math.log(
                (self.doc_count - doc_freq + 0.5) / (doc_freq + 0.5) + 1
            )

    def to_qdrant_sparse(self, text: str) -> Dict:
        """
        Convert to Qdrant sparse vector format.
        
        Args:
            text: Input text
            
        Returns:
            Dict with 'indices' and 'values' keys
        """
        indices, values = self.encode(text)
        return {
            "indices": indices,
            "values": values,
        }


# Global encoder instance (can be configured)
_default_encoder: Optional[BM25SparseEncoder] = None


def get_sparse_encoder() -> BM25SparseEncoder:
    """Get or create default sparse encoder."""
    global _default_encoder
    if _default_encoder is None:
        _default_encoder = BM25SparseEncoder()
    return _default_encoder


def encode_sparse(text: str) -> Tuple[List[int], List[float]]:
    """Convenience function to encode text to sparse vector."""
    return get_sparse_encoder().encode(text)


def encode_sparse_qdrant(text: str) -> Dict:
    """Convenience function to encode text to Qdrant sparse format."""
    return get_sparse_encoder().to_qdrant_sparse(text)
