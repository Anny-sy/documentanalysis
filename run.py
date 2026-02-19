#!/usr/bin/env python
"""Entry point for running the Legal RAG web application."""

import uvicorn
from pathlib import Path

if __name__ == "__main__":
    uvicorn.run(
        "legal_rag.api.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=[str(Path(__file__).parent / "legal_rag")]
    )
