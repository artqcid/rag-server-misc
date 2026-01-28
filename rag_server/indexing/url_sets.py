"""URL set management for indexing contexts."""
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

from .models import ContextConfig, TierConfig

logger = logging.getLogger(__name__)

# Default contexts directory
CONTEXTS_DIR = Path(__file__).parent / "contexts"


class URLSetManager:
    """Manages URL sets for indexing contexts."""
    
    def __init__(self, contexts_dir: Optional[Path] = None):
        """
        Initialize URL set manager.
        
        Args:
            contexts_dir: Directory containing context JSON files
        """
        self.contexts_dir = contexts_dir or CONTEXTS_DIR
        self._contexts: Dict[str, ContextConfig] = {}
        self._loaded = False
    
    def load_all(self) -> None:
        """Load all context configurations from the contexts directory."""
        if not self.contexts_dir.exists():
            logger.warning(f"Contexts directory not found: {self.contexts_dir}")
            return
        
        for json_file in self.contexts_dir.glob("*.json"):
            try:
                self.load_context(json_file)
            except Exception as e:
                logger.error(f"Error loading context {json_file}: {e}")
        
        self._loaded = True
        logger.info(f"Loaded {len(self._contexts)} contexts")
    
    def load_context(self, file_path: Path) -> ContextConfig:
        """
        Load a single context configuration.
        
        Args:
            file_path: Path to context JSON file
            
        Returns:
            Loaded ContextConfig
        """
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Parse tiers
        tiers = {}
        for tier_name, tier_data in data.get("tiers", {}).items():
            tiers[tier_name] = TierConfig(**tier_data)
        
        config = ContextConfig(
            context=data["context"],
            library=data["library"],
            description=data.get("description"),
            collection=data.get("collection"),
            tiers=tiers,
        )
        
        self._contexts[config.context] = config
        logger.debug(f"Loaded context: {config.context} with {len(config.tiers)} tiers")
        
        return config
    
    def get_context(self, name: str) -> Optional[ContextConfig]:
        """
        Get a context configuration by name.
        
        Args:
            name: Context name (e.g., 'juce', 'vue')
            
        Returns:
            ContextConfig or None
        """
        if not self._loaded:
            self.load_all()
        return self._contexts.get(name)
    
    def list_contexts(self) -> List[str]:
        """
        List all available context names.
        
        Returns:
            List of context names
        """
        if not self._loaded:
            self.load_all()
        return sorted(self._contexts.keys())
    
    def get_all_contexts(self) -> Dict[str, ContextConfig]:
        """
        Get all loaded contexts.
        
        Returns:
            Dict of context name to ContextConfig
        """
        if not self._loaded:
            self.load_all()
        return self._contexts.copy()
    
    def get_context_info(self, name: str) -> Optional[dict]:
        """
        Get summary information about a context.
        
        Args:
            name: Context name
            
        Returns:
            Dict with context info or None
        """
        context = self.get_context(name)
        if not context:
            return None
        
        tier_info = {}
        total_urls = 0
        
        for tier_name, tier_config in context.tiers.items():
            urls = tier_config.get_urls()
            tier_info[tier_name] = {
                "description": tier_config.description,
                "doc_type": tier_config.doc_type,
                "source_type": tier_config.source_type,
                "url_count": len(urls),
            }
            total_urls += len(urls)
        
        return {
            "context": context.context,
            "library": context.library,
            "description": context.description,
            "collection": context.get_collection_name(),
            "total_urls": total_urls,
            "tiers": tier_info,
        }
