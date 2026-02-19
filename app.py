"""FastAPI Web Application for Legal Document RAG System."""

import os
import shutil
from pathlib import Path
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

# Global components
components = {}


def get_components():
    """Initialize or return RAG components."""
    if not components:
        from src.document_processor import LegalDocumentProcessor, LegalChunker
        from src.vector_store import ChromaVectorStore
        from src.compression import LLMLinguaCompressor
        from src.rag_engine import LegalRAGEngine
        from src.config import config

        processor = LegalDocumentProcessor()
        chunker = LegalChunker(
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap
        )
        vector_store = ChromaVectorStore(
            persist_directory=config.chroma_persist_dir,
            collection_name=config.collection_name,
            embedding_model=config.embedding_model
        )

        try:
            compressor = LLMLinguaCompressor(target_ratio=config.compression_ratio)
        except Exception:
            from src.compression.llmlingua_compressor import SimpleFallbackCompressor
            compressor = SimpleFallbackCompressor(target_ratio=config.compression_ratio)

        rag_engine = LegalRAGEngine(
            vector_store=vector_store,
            compressor=compressor,
            openai_model=config.openai_model,
            top_k=config.top_k
        )

        components.update({
            "processor": processor,
            "chunker": chunker,
            "vector_store": vector_store,
            "compressor": compressor,
            "rag_engine": rag_engine
        })

    return components


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Create upload directory
    Path("./uploads").mkdir(exist_ok=True)
    # Initialize components
    get_components()
    yield
    # Cleanup
    components.clear()


app = FastAPI(title="Legal Document RAG", lifespan=lifespan)

# Serve static files
app.mount("/static", StaticFiles(directory="static"), name="static")


class QueryRequest(BaseModel):
    question: str


class QueryResponse(BaseModel):
    answer: str
    sources: list[dict]
    token_stats: dict


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main HTML page."""
    html_content = Path("static/index.html").read_text(encoding="utf-8")
    return HTMLResponse(content=html_content)


@app.post("/api/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """Query the RAG system."""
    try:
        comps = get_components()
        rag_engine = comps["rag_engine"]
        response = rag_engine.query(request.question)

        return QueryResponse(
            answer=response.answer,
            sources=response.sources,
            token_stats=response.token_stats
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/upload")
async def upload_document(file: UploadFile = File(...)):
    """Upload and process a document."""
    try:
        comps = get_components()
        processor = comps["processor"]
        chunker = comps["chunker"]
        vector_store = comps["vector_store"]

        # Save uploaded file
        file_path = Path(f"./uploads/{file.filename}")
        with open(file_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        # Process document
        doc = processor.process_file(file_path)
        chunks = chunker.chunk_document(doc)
        vector_store.add_chunks(chunks)

        return {
            "success": True,
            "filename": file.filename,
            "case_name": doc.metadata.case_name,
            "chunks_created": len(chunks)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stats")
async def get_stats():
    """Get collection statistics."""
    try:
        comps = get_components()
        stats = comps["vector_store"].get_collection_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/analyze-case")
async def analyze_case(case_name: str = Form(...)):
    """Analyze a specific case."""
    try:
        comps = get_components()
        rag_engine = comps["rag_engine"]
        response = rag_engine.analyze_case(case_name)

        return QueryResponse(
            answer=response.answer,
            sources=response.sources,
            token_stats=response.token_stats
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/compare-cases")
async def compare_cases(case1: str = Form(...), case2: str = Form(...)):
    """Compare two cases."""
    try:
        comps = get_components()
        rag_engine = comps["rag_engine"]
        response = rag_engine.compare_cases(case1, case2)

        return QueryResponse(
            answer=response.answer,
            sources=response.sources,
            token_stats=response.token_stats
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
