"""Tier-based indexing runner."""
import asyncio
import logging
import time
from typing import Optional, List

from .models import (
    ContextConfig,
    TierConfig,
    FetchResult,
    ProcessedDocument,
    IndexingResult,
    IndexingConfig,
)
from .web_scraper import WebScraper
from .github_fetcher import GitHubFetcher
from .url_sets import URLSetManager

logger = logging.getLogger(__name__)


class TierRunner:
    """Orchestrates tier-based indexing."""
    
    def __init__(
        self,
        url_manager: Optional[URLSetManager] = None,
        config: Optional[IndexingConfig] = None,
        rag_server_url: str = "http://127.0.0.1:8002",
    ):
        """
        Initialize tier runner.
        
        Args:
            url_manager: URL set manager instance
            config: Indexing configuration
            rag_server_url: URL of the RAG server
        """
        self.url_manager = url_manager or URLSetManager()
        self.config = config or IndexingConfig()
        self.rag_server_url = rag_server_url.rstrip("/")
        
        self._web_scraper: Optional[WebScraper] = None
        self._github_fetcher: Optional[GitHubFetcher] = None
    
    async def run_tier(
        self,
        context_name: str,
        tier_name: str,
        collection: Optional[str] = None,
        dry_run: bool = False,
    ) -> IndexingResult:
        """
        Run indexing for a specific tier.
        
        Args:
            context_name: Context identifier (e.g., 'juce')
            tier_name: Tier identifier (e.g., 'tier1_overview')
            collection: Override collection name
            dry_run: If True, only fetch and process, don't index
            
        Returns:
            IndexingResult with statistics
        """
        start_time = time.time()
        
        # Load context
        context = self.url_manager.get_context(context_name)
        if not context:
            return IndexingResult(
                context=context_name,
                tier=tier_name,
                collection="",
                errors=[f"Context '{context_name}' not found"],
            )
        
        # Get tier config
        tier = context.get_tier(tier_name)
        if not tier:
            return IndexingResult(
                context=context_name,
                tier=tier_name,
                collection=collection or context.get_collection_name(),
                errors=[f"Tier '{tier_name}' not found in context '{context_name}'"],
            )
        
        collection_name = collection or context.get_collection_name()
        
        # Get URLs to fetch
        url_items = tier.get_urls()
        total_urls = len(url_items)
        
        logger.info(f"Starting indexing: {context_name}/{tier_name} - {total_urls} URLs")
        
        # Initialize result
        result = IndexingResult(
            context=context_name,
            tier=tier_name,
            collection=collection_name,
            total_urls=total_urls,
        )
        
        if total_urls == 0:
            result.errors.append("No URLs to process")
            result.duration_seconds = time.time() - start_time
            return result
        
        # Fetch content
        fetch_results = await self._fetch_all(url_items, tier.source_type)
        
        successful_results = [r for r in fetch_results if r.success]
        result.successful_fetches = len(successful_results)
        result.failed_fetches = total_urls - result.successful_fetches
        
        # Add failed URLs to errors
        for r in fetch_results:
            if not r.success:
                result.errors.append(f"Failed to fetch {r.url}: {r.error}")
        
        if not successful_results:
            result.duration_seconds = time.time() - start_time
            return result
        
        # Process into documents
        documents = self._process_results(
            successful_results,
            context.library,
            tier.doc_type,
        )
        result.documents_indexed = len(documents)
        
        # Index documents (unless dry run)
        if not dry_run and documents:
            chunks = await self._index_documents(documents, collection_name)
            result.chunks_created = chunks
        elif dry_run:
            logger.info(f"Dry run: Would index {len(documents)} documents")
        
        result.duration_seconds = time.time() - start_time
        logger.info(result.summary())
        
        return result
    
    async def run_all_tiers(
        self,
        context_name: str,
        collection: Optional[str] = None,
        dry_run: bool = False,
    ) -> List[IndexingResult]:
        """
        Run indexing for all tiers in a context.
        
        Args:
            context_name: Context identifier
            collection: Override collection name
            dry_run: If True, only fetch and process, don't index
            
        Returns:
            List of IndexingResults
        """
        context = self.url_manager.get_context(context_name)
        if not context:
            return [IndexingResult(
                context=context_name,
                tier="all",
                collection="",
                errors=[f"Context '{context_name}' not found"],
            )]
        
        results = []
        for tier_name in context.get_tier_names():
            result = await self.run_tier(
                context_name,
                tier_name,
                collection=collection,
                dry_run=dry_run,
            )
            results.append(result)
            
            # Delay between tiers
            if not dry_run:
                await asyncio.sleep(self.config.request_delay)
        
        return results
    
    async def _fetch_all(
        self,
        url_items: List[dict],
        source_type: str,
    ) -> List[FetchResult]:
        """
        Fetch all URLs with appropriate fetcher.
        
        Args:
            url_items: List of URL items with metadata
            source_type: 'web' or 'github'
            
        Returns:
            List of FetchResults
        """
        results = []
        
        # Select fetcher
        if source_type == "github":
            fetcher = GitHubFetcher(self.config)
        else:
            fetcher = WebScraper(self.config)
        
        async with fetcher:
            for item in url_items:
                url = item["url"]
                metadata = item.get("metadata", {})
                
                result = await fetcher.fetch(url, metadata)
                results.append(result)
                
                # Rate limiting
                await asyncio.sleep(self.config.request_delay)
        
        return results
    
    def _process_results(
        self,
        results: List[FetchResult],
        library: str,
        doc_type: str,
    ) -> List[ProcessedDocument]:
        """
        Process fetch results into documents.
        
        Args:
            results: Successful fetch results
            library: Library name for metadata
            doc_type: Document type for metadata
            
        Returns:
            List of ProcessedDocuments
        """
        documents = []
        
        for result in results:
            if not result.content or len(result.content) < 100:
                logger.debug(f"Skipping {result.url}: content too short")
                continue
            
            metadata = {
                **result.metadata,
                "library": library,
                "doc_type": doc_type,
                "language": "en",
                "ingestion_source": "python-indexer",
            }
            
            title = result.metadata.get("title") or self._extract_title_from_url(result.url)
            if title:
                metadata["title"] = title
            
            doc = ProcessedDocument(
                content=result.content,
                metadata=metadata,
                url=result.url,
                title=title,
                char_count=len(result.content),
            )
            documents.append(doc)
        
        return documents
    
    async def _index_documents(
        self,
        documents: List[ProcessedDocument],
        collection: str,
    ) -> int:
        """
        Index documents via RAG server.
        
        Args:
            documents: Documents to index
            collection: Collection name
            
        Returns:
            Total chunks created
        """
        import httpx
        
        total_chunks = 0
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            # Process in batches
            for i in range(0, len(documents), self.config.batch_size):
                batch = documents[i:i + self.config.batch_size]
                
                payload = {
                    "documents": [
                        {
                            "content": doc.content,
                            "metadata": doc.metadata,
                        }
                        for doc in batch
                    ],
                    "collection": collection,
                }
                
                try:
                    response = await client.post(
                        f"{self.rag_server_url}/v1/rag/index",
                        json=payload,
                    )
                    response.raise_for_status()
                    
                    data = response.json()
                    chunks = data.get("chunks_created", 0)
                    total_chunks += chunks
                    
                    logger.debug(f"Indexed batch {i // self.config.batch_size + 1}: {chunks} chunks")
                    
                except Exception as e:
                    logger.error(f"Error indexing batch: {e}")
        
        return total_chunks
    
    def _extract_title_from_url(self, url: str) -> Optional[str]:
        """Extract a title from URL path."""
        if "/" not in url:
            return None
        
        # Get last path segment
        path = url.rstrip("/").split("/")[-1]
        
        # Remove extension
        if "." in path:
            path = path.rsplit(".", 1)[0]
        
        # Clean up
        path = path.replace("-", " ").replace("_", " ")
        
        if path and len(path) > 3:
            return path.title()
        
        return None
