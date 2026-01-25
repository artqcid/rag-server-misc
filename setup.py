"""Setup configuration for rag-server-misc."""
from setuptools import setup, find_packages

setup(
    name="rag-server-misc",
    version="1.0.0",
    description="Local RAG server using Qdrant vector database",
    author="artqcid",
    url="https://github.com/artqcid/rag-server-misc",
    packages=find_packages(),
    python_requires=">=3.9",
    install_requires=[
        "fastapi>=0.104.0",
        "uvicorn>=0.24.0",
        "httpx>=0.27.0",
        "pydantic>=2.5.0",
        "pydantic-settings>=2.0.0",
        "qdrant-client>=1.7.0",
        "python-dotenv>=1.0.0",
    ],
    extras_require={
        "dev": ["pytest", "pytest-asyncio", "httpx"],
    },
    entry_points={
        "console_scripts": [
            "rag-server=rag_server.__main__:main",
        ],
    },
)
