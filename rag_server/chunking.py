"""Text chunking strategies."""
from typing import List
import re


class HybridChunker:
    """Hybrid text chunking using fixed-size + sentence boundaries."""

    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        min_chunk_size: int = 100,
        use_sentence_splitting: bool = True,
    ):
        """
        Initialize chunker.
        
        Args:
            chunk_size: Target chunk size in characters
            chunk_overlap: Overlap between chunks
            min_chunk_size: Minimum chunk size
            use_sentence_splitting: Use sentence boundaries
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size
        self.use_sentence_splitting = use_sentence_splitting

        # Sentence boundary patterns
        self.sentence_pattern = re.compile(r'(?<=[.!?])\s+')

    def chunk(self, text: str) -> List[str]:
        """
        Split text into chunks.
        
        Args:
            text: Text to chunk
            
        Returns:
            List of text chunks
        """
        if not text or len(text) < self.min_chunk_size:
            return [text] if text else []

        if self.use_sentence_splitting:
            return self._hybrid_chunk(text)
        else:
            return self._fixed_size_chunk(text)

    def _fixed_size_chunk(self, text: str) -> List[str]:
        """
        Simple fixed-size chunking with overlap.
        
        Args:
            text: Text to chunk
            
        Returns:
            List of chunks
        """
        chunks = []
        start = 0

        while start < len(text):
            end = start + self.chunk_size
            
            # Get chunk
            chunk = text[start:end].strip()
            
            if chunk:
                chunks.append(chunk)
            
            # Move start position with overlap
            start = end - self.chunk_overlap
            
            # Avoid infinite loop
            if start <= len(chunks) * self.chunk_size - sum(self.chunk_overlap for _ in chunks):
                break

        return chunks

    def _hybrid_chunk(self, text: str) -> List[str]:
        """
        Hybrid chunking using sentence boundaries.
        
        Args:
            text: Text to chunk
            
        Returns:
            List of chunks
        """
        # Split into sentences
        sentences = self.sentence_pattern.split(text)
        if not sentences:
            return [text]

        chunks = []
        current_chunk = []
        current_length = 0

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            sentence_length = len(sentence)

            # Check if adding sentence exceeds chunk size
            if current_length + sentence_length > self.chunk_size and current_chunk:
                # Save current chunk
                chunk_text = " ".join(current_chunk)
                if len(chunk_text) >= self.min_chunk_size:
                    chunks.append(chunk_text)

                # Start new chunk with overlap
                # Keep last few sentences for overlap
                overlap_sentences = []
                overlap_length = 0
                
                for s in reversed(current_chunk):
                    if overlap_length + len(s) <= self.chunk_overlap:
                        overlap_sentences.insert(0, s)
                        overlap_length += len(s)
                    else:
                        break

                current_chunk = overlap_sentences
                current_length = overlap_length

            # Add sentence to current chunk
            current_chunk.append(sentence)
            current_length += sentence_length

        # Add remaining chunk
        if current_chunk:
            chunk_text = " ".join(current_chunk)
            if len(chunk_text) >= self.min_chunk_size:
                chunks.append(chunk_text)

        return chunks if chunks else [text]

    def chunk_with_metadata(self, text: str, base_metadata: dict = None) -> List[dict]:
        """
        Chunk text and attach metadata to each chunk.
        
        Args:
            text: Text to chunk
            base_metadata: Base metadata to attach to all chunks
            
        Returns:
            List of dicts with 'content' and 'metadata' keys
        """
        chunks = self.chunk(text)
        base_metadata = base_metadata or {}

        return [
            {
                "content": chunk,
                "metadata": {
                    **base_metadata,
                    "chunk_index": idx,
                    "total_chunks": len(chunks),
                    "chunk_size": len(chunk),
                },
            }
            for idx, chunk in enumerate(chunks)
        ]
