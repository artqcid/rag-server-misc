"""Main entry point for RAG server."""
import sys
import uvicorn
from .config import RAGConfig
from .server import create_app


def main():
    """Start RAG server."""
    config = RAGConfig.from_env()
    
    print(f"=== RAG Server v1.0.0 ===")
    print(f"Qdrant: {config.qdrant_url}")
    print(f"Embedding: {config.embedding_url}")
    print(f"LLM: {config.llm_url}")
    print(f"Server: http://{config.host}:{config.port}")
    print(f"Collection: {config.qdrant_collection}")
    print(f"========================")
    
    app = create_app(config)
    
    try:
        uvicorn.run(
            app,
            host=config.host,
            port=config.port,
            log_level="info",
        )
    except KeyboardInterrupt:
        print("\nShutting down RAG server...")
        sys.exit(0)


if __name__ == "__main__":
    main()
