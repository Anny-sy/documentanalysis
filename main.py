#!/usr/bin/env python
"""
Legal Document RAG System - Main Entry Point

Usage:
    python main.py web              # Start web server
    python main.py cli              # Run CLI interface
    python main.py ingest <path>    # Ingest documents
    python main.py query "<text>"   # Query documents
    python main.py stats            # Show statistics
"""

import sys
import argparse
from pathlib import Path


def run_web():
    """Start the FastAPI web server."""
    import uvicorn
    print("🚀 Starting Legal Document RAG Web Server...")
    print("📍 Open http://localhost:8000 in your browser")
    print("⏹️  Press Ctrl+C to stop\n")
    uvicorn.run("legal_rag.api.app:app", host="0.0.0.0", port=8000, reload=True)


def run_cli():
    """Run the CLI interface."""
    from legal_rag.cli import main
    main()


def run_ingest(path: str):
    """Ingest documents from a directory."""
    from legal_rag.cli import ingest_documents
    ingest_documents(path)


def run_query(question: str):
    """Query the document corpus."""
    from legal_rag.cli import query_documents
    query_documents(question)


def run_stats():
    """Show collection statistics."""
    from legal_rag.cli import create_components
    from rich.console import Console
    
    console = Console()
    components = create_components()
    stats = components["vector_store"].get_collection_stats()
    
    console.print(f"[bold]Collection:[/bold] {stats['collection_name']}")
    console.print(f"[bold]Documents:[/bold] {stats['document_count']}")
    console.print(f"[bold]Storage:[/bold] {stats.get('persist_directory', 'N/A')}")


def main():
    parser = argparse.ArgumentParser(
        description="Legal Document RAG System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py web                           # Start web server
  python main.py cli                           # Interactive CLI mode
  python main.py ingest ./data/documents       # Ingest documents
  python main.py query "What was the holding?" # Query documents
  python main.py stats                         # Show statistics
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Web command
    subparsers.add_parser("web", help="Start the web server")
    
    # CLI command
    subparsers.add_parser("cli", help="Run CLI interface")
    
    # Ingest command
    ingest_parser = subparsers.add_parser("ingest", help="Ingest documents")
    ingest_parser.add_argument("path", help="Directory containing documents")
    
    # Query command
    query_parser = subparsers.add_parser("query", help="Query documents")
    query_parser.add_argument("question", help="Your question")
    
    # Stats command
    subparsers.add_parser("stats", help="Show statistics")
    
    args = parser.parse_args()
    
    if args.command == "web":
        run_web()
    elif args.command == "cli":
        run_cli()
    elif args.command == "ingest":
        run_ingest(args.path)
    elif args.command == "query":
        run_query(args.question)
    elif args.command == "stats":
        run_stats()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
