"""Test script to verify RAG system components."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))


def test_imports():
    """Test that all modules can be imported."""
    print("Testing imports...")
    
    try:
        from src.config import config
        print("  [OK] config")
    except Exception as e:
        print(f"  [FAIL] config: {e}")
        return False
    
    try:
        from src.document_processor import LegalDocumentProcessor, LegalChunker
        print("  [OK] document_processor")
    except Exception as e:
        print(f"  [FAIL] document_processor: {e}")
        return False
    
    try:
        from src.vector_store import ChromaVectorStore
        print("  [OK] vector_store")
    except Exception as e:
        print(f"  [FAIL] vector_store: {e}")
        return False
    
    try:
        from src.compression import LLMLinguaCompressor
        print("  [OK] compression")
    except Exception as e:
        print(f"  [FAIL] compression: {e}")
        return False
    
    try:
        from src.rag_engine import LegalRAGEngine
        print("  [OK] rag_engine")
    except Exception as e:
        print(f"  [FAIL] rag_engine: {e}")
        return False
    
    print("\nAll imports successful!")
    return True


def test_document_processor():
    """Test document processing with sample text."""
    print("\nTesting document processor...")
    
    from src.document_processor import LegalDocumentProcessor, LegalChunker
    from src.document_processor.legal_document_processor import ProcessedDocument, DocumentMetadata
    
    # Create sample document
    sample_text = """
    SUPREME COURT OF THE UNITED STATES
    
    Brown v. Board of Education, 347 U.S. 483 (1954)
    
    May 17, 1954
    
    OPINION
    
    Chief Justice Warren delivered the opinion of the Court.
    
    These cases come to us from the States of Kansas, South Carolina, 
    Virginia, and Delaware. They are premised on different facts and 
    different local conditions, but a common legal question justifies 
    their consideration together in this consolidated opinion.
    
    HOLDING
    
    We conclude that in the field of public education the doctrine of 
    "separate but equal" has no place. Separate educational facilities 
    are inherently unequal.
    """
    
    processor = LegalDocumentProcessor()
    
    # Test metadata extraction
    metadata = processor._extract_metadata(
        sample_text, 
        Path("test.txt"), 
        "txt", 
        1
    )
    
    print(f"  Case name: {metadata.case_name}")
    print(f"  Court: {metadata.court}")
    print(f"  Citation: {metadata.citation}")
    print(f"  Date: {metadata.date}")
    
    # Test section extraction
    sections = processor._extract_sections(sample_text)
    print(f"  Sections found: {[s['title'] for s in sections]}")
    
    # Test chunking
    chunker = LegalChunker(chunk_size=500, chunk_overlap=50)
    doc = ProcessedDocument(
        content=sample_text,
        metadata=metadata,
        sections=sections
    )
    chunks = chunker.chunk_document(doc)
    print(f"  Chunks created: {len(chunks)}")
    
    print("\nDocument processor test passed!")
    return True


def test_fallback_compressor():
    """Test the fallback compressor (doesn't require LLMLingua)."""
    print("\nTesting fallback compressor...")
    
    from src.compression.llmlingua_compressor import SimpleFallbackCompressor
    
    sample_text = """
    The court held that the defendant's actions constituted a breach of 
    contract. In reaching this conclusion, the court relied on the 
    precedent established in Smith v. Jones, 123 F.3d 456 (2020).
    
    The plaintiff demonstrated that all elements of breach were satisfied.
    First, there was a valid contract between the parties. Second, the 
    defendant failed to perform their obligations. Third, the plaintiff
    suffered damages as a result.
    """
    
    compressor = SimpleFallbackCompressor(target_ratio=0.5)
    result = compressor.compress(sample_text, query="breach of contract")
    
    print(f"  Original tokens: {result.original_tokens}")
    print(f"  Compressed tokens: {result.compressed_tokens}")
    print(f"  Compression ratio: {result.compression_ratio:.2%}")
    
    print("\nFallback compressor test passed!")
    return True


def main():
    """Run all tests."""
    print("=" * 50)
    print("Legal RAG System - Component Tests")
    print("=" * 50)
    
    all_passed = True
    
    if not test_imports():
        all_passed = False
    
    if not test_document_processor():
        all_passed = False
    
    if not test_fallback_compressor():
        all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("All tests passed!")
    else:
        print("Some tests failed. Check output above.")
    print("=" * 50)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
