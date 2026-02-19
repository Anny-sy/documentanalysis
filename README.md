# Legal Document RAG System

A Retrieval-Augmented Generation (RAG) system for analyzing legal documents using compressed prompts. Handles extensive case law across 1000+ page documents while reducing token costs through LLMLingua compression.

## Architecture

```
                   +------------------+
                   |   Legal Documents|
                   |  (PDF/DOCX/TXT)  |
                   +--------+---------+
                            |
                   +--------v---------+
                   | Document Processor|
                   |  - Text extraction|
                   |  - Metadata parse |
                   |  - Section detect |
                   +--------+---------+
                            |
                   +--------v---------+
                   |  Legal Chunker    |
                   |  - Semantic split |
                   |  - Citation-aware |
                   |  - Section-based  |
                   +--------+---------+
                            |
                   +--------v---------+
                   |  ChromaDB Store   |
                   |  - OpenAI embed   |
                   |  - Cosine search  |
                   |  - Metadata filter|
                   +--------+---------+
                            |
              +-------------+-------------+
              |                           |
     +--------v---------+       +--------v---------+
     | LLMLingua Compress|       | Fallback Compress|
     |  - Citation protect|       |  - Extractive    |
     |  - Legal term keep |       |  - Score-based   |
     |  - Query-aware     |       |  - Term density  |
     +--------+---------+       +--------+---------+
              |                           |
              +-------------+-------------+
                            |
                   +--------v---------+
                   |  OpenAI GPT-4     |
                   |  - Legal sys prompt|
                   |  - Cited answers   |
                   +------------------+
```

## Tech Stack

| Component       | Technology                     |
|-----------------|--------------------------------|
| Vector Database | ChromaDB (persistent, cosine)  |
| Embeddings      | OpenAI `text-embedding-3-small`|
| LLM             | OpenAI GPT-4 Turbo             |
| Compression     | LLMLingua 2 (BERT-based)       |
| Doc Processing  | pdfplumber, python-docx        |

## Project Structure

```
legal documentation agent/
|-- main.py                              # CLI entry point
|-- requirements.txt                     # Python dependencies
|-- test_components.py                   # Component tests
|-- .env.example                         # Environment template
|-- data/
|   |-- documents/                       # Place legal documents here
|   |   |-- miranda_v_arizona.txt        # Sample: Miranda v. Arizona
|   |   |-- brown_v_board.txt            # Sample: Brown v. Board of Education
|   |-- chromadb/                        # Vector store persistence (auto-generated)
|-- src/
    |-- __init__.py
    |-- config.py                        # Central configuration
    |-- document_processor/
    |   |-- __init__.py
    |   |-- legal_document_processor.py  # PDF/DOCX/TXT extraction + metadata
    |   |-- chunker.py                   # Legal-aware semantic chunking
    |-- vector_store/
    |   |-- __init__.py
    |   |-- chroma_store.py              # ChromaDB operations
    |-- compression/
    |   |-- __init__.py
    |   |-- llmlingua_compressor.py      # LLMLingua + fallback compressor
    |-- rag_engine/
        |-- __init__.py
        |-- legal_rag.py                 # Core RAG query engine
```

## Setup

### Prerequisites

- Python 3.10+
- An OpenAI API key

### Installation

```bash
# Clone or navigate to the project directory
cd "legal documentation agent"

# Install dependencies
pip install -r requirements.txt

# Create your environment file
cp .env.example .env
```

Edit `.env` and set your OpenAI API key:

```
OPENAI_API_KEY=sk-your-key-here
```

## Usage

### 1. Ingest Documents

Place legal documents (PDF, DOCX, or TXT) into `data/documents/`, then run:

```bash
python main.py ingest ./data/documents
```

This will:
- Extract text from each document
- Detect legal sections (Opinion, Holding, Analysis, etc.)
- Extract metadata (case names, courts, citations, dates)
- Chunk text at semantic boundaries (paragraphs, sections)
- Generate OpenAI embeddings and store them in ChromaDB

### 2. Query Documents

Single question:

```bash
python main.py query "What was the court's holding in Miranda v. Arizona?"
```

### 3. Interactive Mode

```bash
python main.py interactive
```

Interactive commands:
- Type any legal question to query the corpus
- `stats` -- show index statistics
- `help` -- list available commands
- `quit` -- exit

### 4. Check Index Stats

```bash
python main.py stats
```

## Configuration

All settings are controlled via environment variables (`.env` file):

| Variable             | Default                     | Description                          |
|----------------------|-----------------------------|--------------------------------------|
| `OPENAI_API_KEY`     | *(required)*                | OpenAI API key                       |
| `OPENAI_MODEL`       | `gpt-4-turbo-preview`      | LLM model for generation             |
| `EMBEDDING_MODEL`    | `text-embedding-3-small`    | Embedding model for vector search    |
| `CHROMA_PERSIST_DIR` | `./data/chromadb`           | ChromaDB storage directory           |
| `COLLECTION_NAME`    | `legal_documents`           | ChromaDB collection name             |
| `COMPRESSION_RATIO`  | `0.5`                       | Target compression (0.5 = 50%)       |
| `CHUNK_SIZE`         | `1000`                      | Max characters per chunk             |
| `CHUNK_OVERLAP`      | `200`                       | Overlap between consecutive chunks   |
| `TOP_K`              | `10`                        | Number of chunks retrieved per query |

## How It Works

### Document Processing

The `LegalDocumentProcessor` handles three formats:

- **PDF**: Extracted page-by-page via `pdfplumber`
- **DOCX**: Paragraphs extracted via `python-docx`
- **TXT**: Read directly with UTF-8 encoding

Metadata is automatically extracted using regex patterns:
- Case names (`Party A v. Party B`)
- Courts (`Supreme Court of the United States`, etc.)
- Citations (`347 U.S. 483`, `384 U.S. 436`)
- Dates (`May 17, 1954`)

Sections are detected by matching common legal headers: OPINION, BACKGROUND, FACTS, ANALYSIS, DISCUSSION, HOLDING, CONCLUSION, DISSENT, CONCURRENCE, and others.

### Chunking Strategy

The `LegalChunker` splits documents using a **section-first, paragraph-aware** approach:

1. If sections are detected, each section is chunked independently
2. Within sections, splits occur at paragraph boundaries
3. Long paragraphs are further split at sentence boundaries
4. Legal citations (e.g., `123 U.S. 456`, `Id.`, `See`) are protected from mid-citation splits
5. Configurable overlap preserves context across chunk boundaries

### Prompt Compression

Two compression strategies are available:

**LLMLingua (primary)**: Uses Microsoft's `llmlingua-2-bert-base-multilingual-cased-meetingbank` model to remove non-essential tokens. Legal-specific enhancements:
- Citations are replaced with placeholders before compression and restored after
- Legal terms (`holding`, `plaintiff`, `stare decisis`, etc.) are force-preserved
- Query-aware mode prioritizes content relevant to the user's question

**Fallback compressor**: When LLMLingua is unavailable, an extractive approach scores sentences by:
- Legal term density (terms like `court`, `held`, `statute`)
- Citation presence (higher weight)
- Query term overlap

Top-scoring sentences are kept up to the target ratio.

### RAG Pipeline

Each query follows this pipeline:

1. **Retrieve**: ChromaDB cosine similarity search returns top-k chunks, optionally filtered by metadata (case name, court, section)
2. **Compress**: Retrieved context is compressed via LLMLingua (or fallback), reducing token count by ~50%
3. **Generate**: Compressed context + question are sent to GPT-4 with a legal-specialist system prompt
4. **Return**: Answer, source citations, and token usage statistics are returned

### Specialized Query Methods

The `LegalRAGEngine` provides purpose-built methods beyond basic Q&A:

```python
from src.rag_engine import LegalRAGEngine

engine = LegalRAGEngine(vector_store=store, compressor=compressor)

# Analyze a single case
response = engine.analyze_case("Miranda v. Arizona")

# Compare two cases
response = engine.compare_cases("Miranda v. Arizona", "Brown v. Board of Education")

# Find precedents for a legal issue
response = engine.find_precedents("right to counsel during police interrogation")
```

## Programmatic Usage

```python
from dotenv import load_dotenv
load_dotenv()

from src.document_processor import LegalDocumentProcessor, LegalChunker
from src.vector_store import ChromaVectorStore
from src.compression.llmlingua_compressor import SimpleFallbackCompressor
from src.rag_engine import LegalRAGEngine

# 1. Process documents
processor = LegalDocumentProcessor()
chunker = LegalChunker(chunk_size=1000, chunk_overlap=200)

documents = processor.process_directory("./data/documents")
all_chunks = []
for doc in documents:
    all_chunks.extend(chunker.chunk_document(doc))

# 2. Index into vector store
store = ChromaVectorStore(persist_directory="./data/chromadb")
store.add_chunks(all_chunks)

# 3. Query with compression
compressor = SimpleFallbackCompressor(target_ratio=0.5)
engine = LegalRAGEngine(vector_store=store, compressor=compressor)

response = engine.query("What constitutional rights were established in Miranda?")
print(response.answer)
print(f"Token savings: {response.token_stats['savings_percent']:.1f}%")
```

## Testing

Run the component tests (no API key required):

```bash
python test_components.py
```

This verifies:
- All module imports
- Document processing and metadata extraction
- Section detection
- Chunking logic
- Fallback compressor

## Supported Document Formats

| Format | Extension | Library Used  |
|--------|-----------|---------------|
| PDF    | `.pdf`    | pdfplumber    |
| Word   | `.docx`   | python-docx   |
| Text   | `.txt`    | built-in      |

## Token Cost Savings

With LLMLingua compression at the default 0.5 ratio:

| Scenario                     | Without Compression | With Compression | Savings |
|------------------------------|--------------------:|-----------------:|--------:|
| 10 chunks, ~500 tokens each  | ~5,000 tokens       | ~2,500 tokens    | 50%     |
| 20 chunks from 1000-page doc | ~10,000 tokens      | ~5,000 tokens    | 50%     |
| Full retrieval pipeline/query| ~6,000 tokens       | ~3,200 tokens    | 47%     |

Actual savings vary by document content. Legal text with boilerplate typically compresses well; dense statutory language compresses less.
