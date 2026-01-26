"""Text chunking strategies."""
from typing import List, Dict, Any, Optional
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

    def chunk_with_positions(self, text: str) -> List[Dict[str, Any]]:
        """
        Split text into chunks with character positions.
        
        Args:
            text: Text to chunk
            
        Returns:
            List of dicts with 'content', 'start', 'end' keys
        """
        if not text or len(text) < self.min_chunk_size:
            return [{"content": text, "start": 0, "end": len(text)}] if text else []

        if self.use_sentence_splitting:
            return self._hybrid_chunk_with_positions(text)
        else:
            return self._fixed_size_chunk_with_positions(text)

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

    def _fixed_size_chunk_with_positions(self, text: str) -> List[Dict[str, Any]]:
        """Fixed-size chunking with position tracking."""
        chunks = []
        start = 0

        while start < len(text):
            end = min(start + self.chunk_size, len(text))
            chunk = text[start:end].strip()
            
            if chunk:
                # Find actual positions after strip
                actual_start = text.find(chunk, start)
                actual_end = actual_start + len(chunk)
                chunks.append({
                    "content": chunk,
                    "start": actual_start,
                    "end": actual_end
                })
            
            start = end - self.chunk_overlap
            if start >= len(text) or (chunks and start <= chunks[-1]["start"]):
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

    def _hybrid_chunk_with_positions(self, text: str) -> List[Dict[str, Any]]:
        """
        Hybrid chunking with position tracking.
        
        Args:
            text: Text to chunk
            
        Returns:
            List of dicts with 'content', 'start', 'end' keys
        """
        sentences = self.sentence_pattern.split(text)
        if not sentences:
            return [{"content": text, "start": 0, "end": len(text)}]

        chunks = []
        current_chunk = []
        current_length = 0
        current_start = 0

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            sentence_length = len(sentence)
            
            # Find sentence position in original text
            sentence_pos = text.find(sentence, current_start)

            if current_length + sentence_length > self.chunk_size and current_chunk:
                chunk_text = " ".join(current_chunk)
                if len(chunk_text) >= self.min_chunk_size:
                    # Find chunk position in original text
                    chunk_start = text.find(current_chunk[0], max(0, current_start - self.chunk_size))
                    chunk_end = text.find(current_chunk[-1], chunk_start) + len(current_chunk[-1])
                    chunks.append({
                        "content": chunk_text,
                        "start": chunk_start,
                        "end": chunk_end
                    })

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

            current_chunk.append(sentence)
            current_length += sentence_length
            current_start = sentence_pos + sentence_length

        if current_chunk:
            chunk_text = " ".join(current_chunk)
            if len(chunk_text) >= self.min_chunk_size:
                chunk_start = text.find(current_chunk[0], max(0, current_start - self.chunk_size - current_length))
                chunk_end = min(len(text), text.find(current_chunk[-1], chunk_start) + len(current_chunk[-1]))
                chunks.append({
                    "content": chunk_text,
                    "start": chunk_start,
                    "end": chunk_end
                })

        return chunks if chunks else [{"content": text, "start": 0, "end": len(text)}]

    def chunk_with_metadata(self, text: str, base_metadata: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Chunk text and attach full metadata to each chunk.
        
        Setzt automatisch die chunk-spezifischen Felder gemäß ChatGPT-Analyse:
        - chunk_index: 0-basierter Index
        - chunk_char_start: Startposition im Original
        - chunk_char_end: Endposition im Original
        - chunk_size: Größe in Zeichen
        - chunk_overlap: Konfigurierte Überlappung
        - chunk_strategy: Verwendete Strategie
        - total_chunks: Gesamtanzahl
        
        Args:
            text: Text to chunk
            base_metadata: Base metadata to attach to all chunks
            
        Returns:
            List of dicts with 'content' and 'metadata' keys
        """
        chunks_with_pos = self.chunk_with_positions(text)
        base_metadata = base_metadata or {}
        total_chunks = len(chunks_with_pos)
        
        # Determine strategy name
        strategy = "sentence+char" if self.use_sentence_splitting else "fixed"

        return [
            {
                "content": chunk["content"],
                "metadata": {
                    **base_metadata,
                    # Chunk-spezifische Felder (RAG Server setzt diese)
                    "chunk_index": idx,
                    "chunk_char_start": chunk["start"],
                    "chunk_char_end": chunk["end"],
                    "chunk_size": len(chunk["content"]),
                    "chunk_overlap": self.chunk_overlap,
                    "chunk_strategy": strategy,
                    "total_chunks": total_chunks,
                },
            }
            for idx, chunk in enumerate(chunks_with_pos)
        ]
