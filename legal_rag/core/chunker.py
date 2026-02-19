"""Document chunking module."""

import re
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class DocumentChunk:
    """A chunk of a document."""
    content: str
    chunk_id: str
    document_id: str
    section: str = ""
    page_estimate: int = 0
    metadata: dict = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class LegalChunker:
    """Chunks legal documents with citation protection."""
    
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200, respect_sections: bool = True):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.respect_sections = respect_sections
        
    def chunk_document(self, document) -> List[DocumentChunk]:
        """Split document into chunks."""
        chunks = []
        chunk_index = 0
        
        # Get sections or treat whole doc as one section
        sections = document.sections if document.sections else [{"name": "CONTENT", "text": document.content}]
        
        for section in sections:
            section_name = section.get("name", "CONTENT")
            text = section.get("text", "")
            
            if not text.strip():
                continue
            
            # Split into paragraphs
            paragraphs = text.split("\n\n")
            current_chunk = []
            current_size = 0
            
            for paragraph in paragraphs:
                paragraph = paragraph.strip()
                if not paragraph:
                    continue
                
                # If paragraph is too long, split into sentences
                if len(paragraph) > self.chunk_size:
                    sentences = self._split_sentences(paragraph)
                    for sentence in sentences:
                        if current_size + len(sentence) > self.chunk_size and current_chunk:
                            # Save current chunk
                            chunk_text = " ".join(current_chunk)
                            chunks.append(self._create_chunk(
                                chunk_text, document, section_name, chunk_index
                            ))
                            chunk_index += 1
                            
                            # Start new chunk with overlap
                            overlap_text = self._get_overlap(current_chunk)
                            current_chunk = [overlap_text, sentence] if overlap_text else [sentence]
                            current_size = len(current_chunk[0]) + len(sentence) if current_chunk else len(sentence)
                        else:
                            current_chunk.append(sentence)
                            current_size += len(sentence)
                else:
                    if current_size + len(paragraph) > self.chunk_size and current_chunk:
                        # Save current chunk
                        chunk_text = "\n\n".join(current_chunk)
                        chunks.append(self._create_chunk(
                            chunk_text, document, section_name, chunk_index
                        ))
                        chunk_index += 1
                        
                        # Start new chunk with overlap
                        overlap_text = self._get_overlap(current_chunk)
                        current_chunk = [overlap_text, paragraph] if overlap_text else [paragraph]
                        current_size = len(overlap_text) + len(paragraph) if overlap_text else len(paragraph)
                    else:
                        current_chunk.append(paragraph)
                        current_size += len(paragraph)
            
            # Don't forget the last chunk in this section
            if current_chunk:
                chunk_text = "\n\n".join(current_chunk)
                chunks.append(self._create_chunk(
                    chunk_text, document, section_name, chunk_index
                ))
                chunk_index += 1
        
        return chunks
    
    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences, protecting citations."""
        # Simple sentence splitting
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _get_overlap(self, chunks: List[str]) -> str:
        """Get overlap text from previous chunks."""
        if not chunks or self.chunk_overlap <= 0:
            return ""
        
        overlap_text = ""
        for chunk in reversed(chunks):
            if len(overlap_text) + len(chunk) <= self.chunk_overlap:
                overlap_text = chunk + " " + overlap_text
            else:
                remaining = self.chunk_overlap - len(overlap_text)
                if remaining > 0:
                    overlap_text = chunk[-remaining:] + " " + overlap_text
                break
        
        return overlap_text.strip()
    
    def _create_chunk(self, text: str, document, section: str, index: int) -> DocumentChunk:
        """Create a DocumentChunk from text."""
        doc_id = getattr(document.metadata, 'filename', 'unknown') if hasattr(document, 'metadata') else 'unknown'
        
        return DocumentChunk(
            content=text,
            chunk_id=f"{doc_id}_{section}_{index}",
            document_id=doc_id,
            section=section,
            metadata={
                "case_name": getattr(document.metadata, 'case_name', '') if hasattr(document, 'metadata') else '',
                "court": getattr(document.metadata, 'court', '') if hasattr(document, 'metadata') else '',
                "filename": doc_id,
            }
        )
