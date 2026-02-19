"""Legal Document RAG System with Compressed Prompts."""

__version__ = "1.0.0"
__author__ = "Your Name"

from legal_rag.core.config import Config
from legal_rag.core.legal_document_processor import LegalDocumentProcessor, LegalChunker
from legal_rag.core.chroma_store import ChromaVectorStore
from legal_rag.core.llmlingua_compressor import LLMLinguaCompressor
from legal_rag.core.legal_rag import LegalRAGEngine, RAGResponse

__all__ = [
    "Config",
    "LegalDocumentProcessor",
    "LegalChunker",
    "ChromaVectorStore",
    "LLMLinguaCompressor",
    "LegalRAGEngine",
    "RAGResponse",
]
