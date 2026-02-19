"""
Legal Document RAG System - CLI Interface

Usage:
    python -m legal_rag.cli ingest ./documents
    python -m legal_rag.cli query "What is the holding?"
    python -m legal_rag.cli interactive
"""

import sys
import argparse
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

console = Console()


def create_components():
    """Create and return RAG system components."""
    from legal_rag.core.legal_document_processor import LegalDocumentProcessor, LegalChunker
    from legal_rag.core.chroma_store import ChromaVectorStore
    from legal_rag.core.llmlingua_compressor import LLMLinguaCompressor
    from legal_rag.core.legal_rag import LegalRAGEngine
    from legal_rag.core.config import config
    
    # Initialize components
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
    
    # Try to initialize LLMLingua (may fail on some systems)
    try:
        compressor = LLMLinguaCompressor(
            target_ratio=config.compression_ratio
        )
    except Exception as e:
        console.print(f"[yellow]LLMLingua not available: {e}[/yellow]")
        console.print("[yellow]Using fallback compression[/yellow]")
        from legal_rag.core.llmlingua_compressor import SimpleFallbackCompressor
        compressor = SimpleFallbackCompressor(target_ratio=config.compression_ratio)
    
    rag_engine = LegalRAGEngine(
        vector_store=vector_store,
        compressor=compressor,
        openai_model=config.openai_model,
        top_k=config.top_k
    )
    
    return {
        "processor": processor,
        "chunker": chunker,
        "vector_store": vector_store,
        "compressor": compressor,
        "rag_engine": rag_engine
    }


def ingest_documents(directory: str):
    """Ingest documents from a directory."""
    console.print(Panel.fit(
        "[bold blue]Legal Document Ingestion[/bold blue]",
        subtitle="Processing and indexing documents"
    ))
    
    directory = Path(directory)
    if not directory.exists():
        console.print(f"[red]Directory not found: {directory}[/red]")
        return
    
    components = create_components()
    processor = components["processor"]
    chunker = components["chunker"]
    vector_store = components["vector_store"]
    
    # Process documents
    console.print(f"\n[bold]Processing documents from: {directory}[/bold]")
    documents = processor.process_directory(directory)
    
    if not documents:
        console.print("[yellow]No documents found to process[/yellow]")
        return
    
    console.print(f"[green]Processed {len(documents)} documents[/green]")
    
    # Chunk documents
    console.print("\n[bold]Chunking documents...[/bold]")
    all_chunks = []
    for doc in documents:
        chunks = chunker.chunk_document(doc)
        all_chunks.extend(chunks)
    
    console.print(f"[green]Created {len(all_chunks)} chunks[/green]")
    
    # Index chunks
    console.print("\n[bold]Indexing in vector store...[/bold]")
    vector_store.add_chunks(all_chunks)
    
    # Print stats
    stats = vector_store.get_collection_stats()
    console.print(f"\n[bold green]Ingestion complete![/bold green]")
    console.print(f"Total documents in store: {stats['document_count']}")


def query_documents(question: str):
    """Query the document corpus."""
    console.print(Panel.fit(
        "[bold blue]Legal Document Query[/bold blue]",
        subtitle="Querying with compressed context"
    ))
    
    components = create_components()
    rag_engine = components["rag_engine"]
    
    console.print(f"\n[bold]Question:[/bold] {question}\n")
    
    response = rag_engine.query(question)
    
    # Display answer
    console.print(Panel(
        Markdown(response.answer),
        title="[bold green]Answer[/bold green]",
        expand=False
    ))
    
    # Display token stats
    stats = response.token_stats
    console.print(f"\n[dim]Token usage: {stats['original']} -> {stats['compressed']} "
                  f"({stats['savings_percent']:.1f}% savings)[/dim]")
    
    # Display sources
    if response.sources:
        console.print(f"\n[bold]Sources ({len(response.sources)} chunks):[/bold]")
        for i, source in enumerate(response.sources[:5], 1):
            metadata = source.get("metadata", {})
            case = metadata.get("case_name", "Unknown")
            section = metadata.get("section", "")
            console.print(f"  {i}. {case}" + (f" - {section}" if section else ""))


def interactive_mode():
    """Run interactive query mode."""
    console.print(Panel.fit(
        "[bold blue]Legal Document RAG - Interactive Mode[/bold blue]",
        subtitle="Type 'quit' to exit, 'stats' for index stats"
    ))
    
    components = create_components()
    rag_engine = components["rag_engine"]
    vector_store = components["vector_store"]
    
    while True:
        try:
            console.print()
            question = console.input("[bold cyan]Your question:[/bold cyan] ")
            
            if not question.strip():
                continue
            
            if question.lower() in ("quit", "exit", "q"):
                console.print("[yellow]Goodbye![/yellow]")
                break
            
            if question.lower() == "stats":
                stats = vector_store.get_collection_stats()
                console.print(f"Collection: {stats['collection_name']}")
                console.print(f"Documents: {stats['document_count']}")
                continue
            
            if question.lower() == "help":
                console.print("""
Commands:
  stats  - Show index statistics
  quit   - Exit interactive mode
  help   - Show this help message
  
Or type any legal question to query the document corpus.
                """)
                continue
            
            # Process query
            response = rag_engine.query(question)
            
            console.print()
            console.print(Panel(
                Markdown(response.answer),
                title="[bold green]Answer[/bold green]",
                expand=False
            ))
            
            stats = response.token_stats
            console.print(f"\n[dim]Tokens: {stats['original']} -> {stats['compressed']} "
                          f"({stats['savings_percent']:.1f}% savings)[/dim]")
            
        except KeyboardInterrupt:
            console.print("\n[yellow]Interrupted. Goodbye![/yellow]")
            break
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Legal Document RAG System with Compressed Prompts",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m legal_rag.cli ingest ./data/documents
  python -m legal_rag.cli query "What was the court's holding in Brown v. Board?"
  python -m legal_rag.cli interactive
  python -m legal_rag.cli stats
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Ingest command
    ingest_parser = subparsers.add_parser("ingest", help="Ingest documents from a directory")
    ingest_parser.add_argument("directory", help="Directory containing legal documents")
    
    # Query command
    query_parser = subparsers.add_parser("query", help="Query the document corpus")
    query_parser.add_argument("question", help="Legal question to answer")
    
    # Interactive mode
    subparsers.add_parser("interactive", help="Enter interactive query mode")
    
    # Stats command
    subparsers.add_parser("stats", help="Show index statistics")
    
    args = parser.parse_args()
    
    if args.command == "ingest":
        ingest_documents(args.directory)
    elif args.command == "query":
        query_documents(args.question)
    elif args.command == "interactive":
        interactive_mode()
    elif args.command == "stats":
        components = create_components()
        stats = components["vector_store"].get_collection_stats()
        console.print(f"Collection: {stats['collection_name']}")
        console.print(f"Documents: {stats['document_count']}")
        console.print(f"Storage: {stats['persist_directory']}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
