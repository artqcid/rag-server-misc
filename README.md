# RAG Server (Miscellaneous)

Local RAG (Retrieval-Augmented Generation) server using Qdrant for vector storage and native Continue integration.

## Features

- **Vector Database**: Native Qdrant support (portable binary)
- **Embedding Integration**: Uses local embedding-server-misc (Port 8001)
- **LLM Integration**: Uses local LLM server (Port 8080)
- **Hybrid Chunking**: Fixed-size + sentence-based strategies
- **FastAPI Server**: RESTful API on Port 8002
- **Auto Collection Management**: Creates collections on startup

## Architecture

```
RAG Server (Port 8002)
    ├── Vector DB: Qdrant (Port 6333)
    ├── Embeddings: embedding-server-misc (Port 8001)
    └── LLM: llama.cpp server (Port 8080)
```

## Installation

### 1. Install Qdrant (Windows Portable Binary)

See [qdrant_setup.md](qdrant_setup.md) for detailed instructions.

Quick start:
```powershell
# Download from https://github.com/qdrant/qdrant/releases
# Extract to C:\qdrant\
C:\qdrant\qdrant.exe
```

### 2. Install Python Dependencies

```powershell
# Create virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Or install as package
pip install -e .
```

## Usage

### Start Server

```powershell
# Start with defaults (requires Qdrant, Embedding, LLM running)
.\start.ps1

# Custom port
.\start.ps1 -Port 8003

# Custom Qdrant URL
.\start.ps1 -QdrantUrl "http://192.168.1.100:6333"

# Or via Python module
python -m rag_server
```

### API Endpoints

**Index Documents**
```bash
POST http://127.0.0.1:8002/v1/rag/index
{
  "documents": [
    {
      "content": "Document text...",
      "metadata": {"source": "file.txt", "page": 1}
    }
  ],
  "collection": "documents"
}
```

**RAG Query** (Retrieve + Generate)
```bash
POST http://127.0.0.1:8002/v1/rag/query
{
  "query": "What is the main topic?",
  "limit": 5,
  "include_context": true
}
```

**Vector Search** (Retrieve only)
```bash
POST http://127.0.0.1:8002/v1/rag/search
{
  "query": "search terms",
  "limit": 10
}
```

**Delete Documents**
```bash
DELETE http://127.0.0.1:8002/v1/rag/documents/{doc_id}
```

**Health Check**
```bash
GET http://127.0.0.1:8002/health
```

## Configuration

Environment variables (optional):

```powershell
$env:RAG_PORT = "8002"
$env:RAG_QDRANT_URL = "http://localhost:6333"
$env:RAG_QDRANT_COLLECTION = "documents"
$env:RAG_EMBEDDING_URL = "http://127.0.0.1:8001/v1/embeddings"
$env:RAG_LLM_URL = "http://127.0.0.1:8080/v1/chat/completions"
$env:RAG_CHUNK_SIZE = "512"
$env:RAG_RETRIEVAL_LIMIT = "5"
```

## Continue Integration

Add to `.continue/config.yaml`:

```yaml
mcpServers:
  - name: rag-context
    command: "${workspaceFolder}/rag-server-misc/.venv/Scripts/python.exe"
    args:
      - -m
      - rag_server
    env:
      RAG_PORT: "8002"
      RAG_QDRANT_URL: "http://localhost:6333"
```

## Project Structure

```
rag-server-misc/
├── rag_server/
│   ├── __init__.py
│   ├── __main__.py           # Entry point
│   ├── server.py             # FastAPI server
│   ├── config.py             # Configuration
│   ├── models.py             # Pydantic models
│   ├── vector_db/
│   │   ├── interface.py      # Abstract base
│   │   └── qdrant_client.py  # Qdrant implementation
│   ├── embeddings.py         # Embedding client
│   ├── llm_client.py         # LLM client
│   ├── query_engine.py       # RAG pipeline
│   └── chunking.py           # Text chunking
└── tests/
```

## Dependencies

- **qdrant-client**: Native Qdrant Python client
- **FastAPI**: Web server framework
- **httpx**: Async HTTP client (for embedding/LLM servers)
- **pydantic**: Data validation and settings

## License

MIT License

## Related Projects

- [embedding-server-misc](https://github.com/artqcid/embedding-server-misc)
- [mcp-server-misc](https://github.com/artqcid/mcp-server-misc)
