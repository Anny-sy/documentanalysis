# Legal Document RAG System

## Overview
A Retrieval-Augmented Generation (RAG) system for legal document analysis with LLMLingua prompt compression (~50% token reduction).

## Architecture
```
User Query → RAG Engine → Vector Store (ChromaDB) → LLMLingua Compressor → GPT-4 → Response
```

## Project Structure
```
legal documentation agent/
├── main.py                    # CLI entry point
├── requirements.txt           # Dependencies
├── test_components.py         # Test suite
├── .env.example               # Environment template
├── data/documents/            # Input documents
├── data/chromadb/             # Vector store
└── src/
    ├── config.py              # Configuration
    ├── document_processor/    # Text extraction, chunking
    ├── vector_store/          # ChromaDB integration
    ├── compression/           # LLMLingua compression
    └── rag_engine/            # Query orchestration
```

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Edit .env: OPENAI_API_KEY=your_key

# 3. Test installation
python test_components.py

# 4. Ingest documents
python main.py ingest ./data/documents

# 5. Query
python main.py query "What was the holding in Miranda v. Arizona?"

# 6. Interactive mode
python main.py interactive
```

## Configuration (.env)
| Variable | Required | Default |
|----------|----------|---------|
| OPENAI_API_KEY | Yes | - |
| OPENAI_MODEL | No | gpt-4-turbo-preview |
| EMBEDDING_MODEL | No | text-embedding-3-small |
| COMPRESSION_RATIO | No | 0.5 |
| CHUNK_SIZE | No | 1000 |
| TOP_K | No | 10 |

## Key Components

| Component | Purpose |
|-----------|---------|
| LegalDocumentProcessor | Extract text from PDF/DOCX/TXT, parse metadata |
| LegalChunker | Section-aware chunking with citation protection |
| ChromaVectorStore | Vector storage with metadata filtering |
| LLMLinguaCompressor | Token-level compression preserving citations |
| LegalRAGEngine | End-to-end query pipeline |

## API Usage

```python
from src.document_processor import LegalDocumentProcessor, LegalChunker
from src.vector_store import ChromaVectorStore
from src.rag_engine import LegalRAGEngine

# Ingest
processor = LegalDocumentProcessor()
chunker = LegalChunker()
docs = processor.process_directory("./data/documents")
chunks = [c for d in docs for c in chunker.chunk_document(d)]

store = ChromaVectorStore()
store.add_chunks(chunks)

# Query
engine = LegalRAGEngine(vector_store=store)
response = engine.query("What constitutional rights were established?")
print(response.answer)
print(f"Token savings: {response.token_stats['savings_percent']:.1f}%")
```

## CLI Commands
| Command | Description |
|---------|-------------|
| `ingest <path>` | Process and index documents |
| `query "<question>"` | Single question query |
| `interactive` | Persistent session mode |
| `stats` | Show collection statistics |

## How Compression Works
1. **Citation Protection**: Legal citations replaced with placeholders
2. **Token Scoring**: BERT model scores token importance
3. **Pruning**: Low-importance tokens removed
4. **Restoration**: Citations restored to compressed text

Result: ~50% token reduction while preserving legal meaning and citations.

## Limitations
- English-only metadata extraction
- No OCR for scanned PDFs
- Single-user CLI (no web interface)
- ~500MB LLMLingua model download

## Future Enhancements
- Web UI (FastAPI + React/Streamlit)
- Cross-encoder reranking
- Multi-language support
- OCR integration
- Streaming responses
