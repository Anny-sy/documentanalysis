"""Configuration management for the Legal RAG System."""

import os
from pathlib import Path
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    """Application configuration."""
    
    # API Keys
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    
    # Models
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4-turbo-preview")
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    
    # ChromaDB
    chroma_persist_dir: str = os.getenv("CHROMA_PERSIST_DIR", "./data/chromadb")
    collection_name: str = os.getenv("COLLECTION_NAME", "legal_documents")
    
    # Compression Settings
    compression_ratio: float = float(os.getenv("COMPRESSION_RATIO", "0.5"))
    compression_rate: float = float(os.getenv("COMPRESSION_RATE", "0.55"))
    
    # Chunk Settings
    chunk_size: int = int(os.getenv("CHUNK_SIZE", "1000"))
    chunk_overlap: int = int(os.getenv("CHUNK_OVERLAP", "200"))
    
    # Retrieval Settings
    top_k: int = int(os.getenv("TOP_K", "10"))
    rerank_top_k: int = int(os.getenv("RERANK_TOP_K", "5"))
    
    # Paths - Project root is 2 levels up from config (backend/core/ -> backend/ -> root)
    base_dir: Path = Path(__file__).parent.parent.parent
    documents_dir: Path = base_dir / "data" / "documents"
    
    def validate(self) -> bool:
        """Validate required configuration."""
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required. Set it in .env file.")
        return True


config = Config()
