"""Intelligent chunking for legal documents."""

import re
from typing import Optional
from dataclasses import dataclass

from .legal_document_processor import ProcessedDocument


@dataclass
class DocumentChunk:
    """Represents a chunk of a legal document."""
    
    content: str
    chunk_id: str
    document_id: str
    section: Optional[str] = None
    page_estimate: Optional[int] = None
    metadata: dict = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class LegalChunker:
    """
    Intelligent chunking for legal documents.
    
    Uses semantic boundaries (paragraphs, sections) rather than
    arbitrary character splits to maintain context.
    """
    
    # Legal-specific sentence enders that shouldn't split
    CITATION_PATTERNS = [
        r'\d+\s+U\.S\.',
        r'\d+\s+F\.\d+d',
        r'\d+\s+S\.Ct\.',
        r'Id\.',
        r'See\s+',
        r'Cf\.',
    ]
    
    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        respect_sections: bool = True
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.respect_sections = respect_sections
    
    def chunk_document(self, document: ProcessedDocument) -> list[DocumentChunk]:
        """Chunk a processed document into smaller pieces."""
        chunks = []
        doc_id = document.metadata.filename
        
        if self.respect_sections and document.sections:
            # Chunk by sections first
            for section in document.sections:
                section_chunks = self._chunk_text(
                    section["content"],
                    doc_id,
                    section["title"]
                )
                chunks.extend(section_chunks)
        else:
            # Chunk entire document
            chunks = self._chunk_text(document.content, doc_id)
        
        # Add document-level metadata to all chunks
        for chunk in chunks:
            chunk.metadata.update({
                "case_name": document.metadata.case_name,
                "court": document.metadata.court,
                "date": document.metadata.date,
                "citation": document.metadata.citation,
                "filename": document.metadata.filename
            })
        
        return chunks
    
    def _chunk_text(
        self,
        text: str,
        doc_id: str,
        section: Optional[str] = None
    ) -> list[DocumentChunk]:
        """Chunk text using semantic boundaries."""
        chunks = []
        
        # Split into paragraphs first
        paragraphs = self._split_into_paragraphs(text)
        
        current_chunk = ""
        chunk_idx = 0
        
        for para in paragraphs:
            # If adding this paragraph exceeds chunk size
            if len(current_chunk) + len(para) > self.chunk_size:
                if current_chunk.strip():
                    chunks.append(DocumentChunk(
                        content=current_chunk.strip(),
                        chunk_id=f"{doc_id}_{section or 'main'}_{chunk_idx}",
                        document_id=doc_id,
                        section=section,
                        metadata={}
                    ))
                    chunk_idx += 1
                
                # Handle overlap
                if self.chunk_overlap > 0 and current_chunk:
                    overlap_text = current_chunk[-self.chunk_overlap:]
                    current_chunk = overlap_text + "\n\n" + para
                else:
                    current_chunk = para
            else:
                current_chunk += "\n\n" + para if current_chunk else para
        
        # Add final chunk
        if current_chunk.strip():
            chunks.append(DocumentChunk(
                content=current_chunk.strip(),
                chunk_id=f"{doc_id}_{section or 'main'}_{chunk_idx}",
                document_id=doc_id,
                section=section,
                metadata={}
            ))
        
        return chunks
    
    def _split_into_paragraphs(self, text: str) -> list[str]:
        """Split text into paragraphs, preserving legal formatting."""
        # Split on double newlines
        raw_paragraphs = re.split(r'\n\s*\n', text)
        
        paragraphs = []
        for para in raw_paragraphs:
            para = para.strip()
            if not para:
                continue
            
            # If paragraph is too long, split on sentences
            if len(para) > self.chunk_size:
                sentences = self._split_into_sentences(para)
                paragraphs.extend(sentences)
            else:
                paragraphs.append(para)
        
        return paragraphs
    
    def _split_into_sentences(self, text: str) -> list[str]:
        """Split text into sentences, being careful with legal citations."""
        # Protect common legal abbreviations
        protected_text = text
        protections = []
        
        # Protect citations and abbreviations
        for i, pattern in enumerate(self.CITATION_PATTERNS):
            matches = list(re.finditer(pattern, protected_text))
            for match in matches:
                placeholder = f"__PROTECTED_{i}_{len(protections)}__"
                protections.append((placeholder, match.group()))
                protected_text = protected_text.replace(match.group(), placeholder, 1)
        
        # Split on sentence boundaries
        sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', protected_text)
        
        # Restore protected text
        result = []
        for sentence in sentences:
            for placeholder, original in protections:
                sentence = sentence.replace(placeholder, original)
            if sentence.strip():
                result.append(sentence.strip())
        
        return result
    
    def estimate_tokens(self, text: str) -> int:
        """Rough token estimation (4 chars per token average)."""
        return len(text) // 4
