"""LLMLingua-based prompt compression for legal documents."""

import re
from typing import Optional
from dataclasses import dataclass

from rich.console import Console

console = Console()


@dataclass
class CompressionResult:
    """Result of prompt compression."""
    
    compressed_text: str
    original_tokens: int
    compressed_tokens: int
    compression_ratio: float
    preserved_citations: list[str]


class LLMLinguaCompressor:
    """
    Prompt compression using LLMLingua optimized for legal documents.
    
    LLMLingua uses a small language model to identify and remove
    non-essential tokens while preserving meaning. This implementation
    adds legal-specific optimizations:
    
    - Preserves legal citations (case names, statutory references)
    - Maintains key legal terminology
    - Protects holdings and conclusions
    """
    
    # Legal terms that should be preserved
    LEGAL_PRESERVE_TERMS = [
        "holding", "held", "affirmed", "reversed", "remanded",
        "plaintiff", "defendant", "appellant", "appellee",
        "judgment", "order", "motion", "petition", "writ",
        "statute", "regulation", "constitutional", "amendment",
        "precedent", "stare decisis", "ratio decidendi",
        "obiter dictum", "prima facie", "de facto", "de jure"
    ]
    
    # Citation patterns to protect
    CITATION_PATTERNS = [
        r'\d+\s+U\.S\.\s+\d+',  # US Reports
        r'\d+\s+S\.\s*Ct\.\s+\d+',  # Supreme Court Reporter
        r'\d+\s+F\.\d+d\s+\d+',  # Federal Reporter
        r'\d+\s+F\.\s*Supp\.\s*\d*d?\s+\d+',  # Federal Supplement
        r'[A-Z][a-z]+\s+v\.\s+[A-Z][a-z]+',  # Case names
        r'\d+\s+U\.S\.C\.\s+§\s*\d+',  # USC citations
        r'\d+\s+C\.F\.R\.\s+§\s*\d+',  # CFR citations
    ]
    
    def __init__(
        self,
        model_name: str = "microsoft/llmlingua-2-bert-base-multilingual-cased-meetingbank",
        target_ratio: float = 0.5,
        force_tokens: Optional[list[str]] = None,
        use_gpu: bool = False
    ):
        """
        Initialize the LLMLingua compressor.
        
        Args:
            model_name: HuggingFace model for compression
            target_ratio: Target compression ratio (0.5 = 50% of original)
            force_tokens: Additional tokens to preserve
            use_gpu: Whether to use GPU acceleration
        """
        self.model_name = model_name
        self.target_ratio = target_ratio
        self.force_tokens = force_tokens or []
        self.use_gpu = use_gpu
        
        self._compressor = None
        self._initialized = False
    
    def _ensure_initialized(self):
        """Lazy initialization of LLMLingua."""
        if self._initialized:
            return
        
        try:
            from llmlingua import PromptCompressor
        except ImportError:
            raise ImportError(
                "llmlingua is required. Install with: pip install llmlingua"
            )
        
        device = "cuda" if self.use_gpu else "cpu"
        
        console.print(f"[blue]Loading LLMLingua model: {self.model_name}[/blue]")
        
        self._compressor = PromptCompressor(
            model_name=self.model_name,
            device_map=device
        )
        
        self._initialized = True
        console.print("[green]LLMLingua compressor initialized[/green]")
    
    def compress(
        self,
        text: str,
        query: Optional[str] = None,
        preserve_citations: bool = True
    ) -> CompressionResult:
        """
        Compress text while preserving legal semantics.
        
        Args:
            text: Text to compress
            query: Optional query to guide compression (keeps relevant content)
            preserve_citations: Whether to protect legal citations
            
        Returns:
            CompressionResult with compressed text and statistics
        """
        self._ensure_initialized()
        
        # Extract citations to preserve
        preserved_citations = []
        if preserve_citations:
            preserved_citations = self._extract_citations(text)
        
        # Build force tokens list
        force_tokens = list(self.force_tokens)
        force_tokens.extend(self.LEGAL_PRESERVE_TERMS)
        
        # Protect citations by marking them
        protected_text, citation_map = self._protect_citations(text)
        
        # Estimate original tokens
        original_tokens = self._estimate_tokens(text)
        
        # Compress using LLMLingua
        if query:
            # Query-aware compression
            result = self._compressor.compress_prompt(
                context=[protected_text],
                question=query,
                rate=self.target_ratio,
                force_tokens=force_tokens,
                drop_consecutive=True
            )
        else:
            # Standard compression
            result = self._compressor.compress_prompt(
                context=[protected_text],
                rate=self.target_ratio,
                force_tokens=force_tokens,
                drop_consecutive=True
            )
        
        compressed_text = result.get("compressed_prompt", protected_text)
        
        # Restore protected citations
        compressed_text = self._restore_citations(compressed_text, citation_map)
        
        # Calculate statistics
        compressed_tokens = self._estimate_tokens(compressed_text)
        compression_ratio = compressed_tokens / original_tokens if original_tokens > 0 else 1.0
        
        return CompressionResult(
            compressed_text=compressed_text,
            original_tokens=original_tokens,
            compressed_tokens=compressed_tokens,
            compression_ratio=compression_ratio,
            preserved_citations=preserved_citations
        )
    
    def compress_chunks(
        self,
        chunks: list[dict],
        query: str,
        max_output_tokens: int = 4000
    ) -> str:
        """
        Compress multiple chunks into a single context.
        
        Args:
            chunks: List of retrieved chunks
            query: User query
            max_output_tokens: Maximum tokens in output
            
        Returns:
            Compressed context string
        """
        self._ensure_initialized()
        
        # Combine chunks with separators
        combined_text = "\n\n---\n\n".join([
            f"[Source: {c.get('metadata', {}).get('filename', 'Unknown')}]\n{c['content']}"
            for c in chunks
        ])
        
        # Calculate required compression ratio
        current_tokens = self._estimate_tokens(combined_text)
        required_ratio = min(max_output_tokens / current_tokens, 1.0) if current_tokens > 0 else 1.0
        
        # Use more aggressive compression if needed
        original_ratio = self.target_ratio
        if required_ratio < self.target_ratio:
            self.target_ratio = required_ratio * 0.9  # 10% buffer
        
        result = self.compress(combined_text, query=query)
        
        # Restore original ratio
        self.target_ratio = original_ratio
        
        return result.compressed_text
    
    def _extract_citations(self, text: str) -> list[str]:
        """Extract all legal citations from text."""
        citations = []
        for pattern in self.CITATION_PATTERNS:
            matches = re.findall(pattern, text)
            citations.extend(matches)
        return list(set(citations))
    
    def _protect_citations(self, text: str) -> tuple[str, dict]:
        """Replace citations with placeholders to protect them."""
        citation_map = {}
        protected_text = text
        
        for i, pattern in enumerate(self.CITATION_PATTERNS):
            matches = re.finditer(pattern, protected_text)
            for j, match in enumerate(matches):
                placeholder = f"__CITATION_{i}_{j}__"
                citation_map[placeholder] = match.group()
                protected_text = protected_text.replace(match.group(), placeholder, 1)
        
        return protected_text, citation_map
    
    def _restore_citations(self, text: str, citation_map: dict) -> str:
        """Restore protected citations."""
        restored_text = text
        for placeholder, citation in citation_map.items():
            restored_text = restored_text.replace(placeholder, citation)
        return restored_text
    
    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count (roughly 4 chars per token)."""
        return len(text) // 4
    
    def get_compression_stats(self, result: CompressionResult) -> str:
        """Format compression statistics as string."""
        savings_pct = (1 - result.compression_ratio) * 100
        return (
            f"Compression: {result.original_tokens} -> {result.compressed_tokens} tokens "
            f"({result.compression_ratio:.1%} of original, {savings_pct:.1f}% savings)"
        )


class SimpleFallbackCompressor:
    """
    Simple fallback compressor when LLMLingua is not available.
    
    Uses extractive summarization techniques:
    - Sentence scoring based on legal term density
    - Citation preservation
    - Key section retention
    """
    
    def __init__(self, target_ratio: float = 0.5):
        self.target_ratio = target_ratio
    
    def compress(
        self,
        text: str,
        query: Optional[str] = None
    ) -> CompressionResult:
        """Compress text using extractive methods."""
        sentences = self._split_sentences(text)
        
        # Score sentences
        scored_sentences = []
        for sent in sentences:
            score = self._score_sentence(sent, query)
            scored_sentences.append((sent, score))
        
        # Sort by score and select top sentences
        scored_sentences.sort(key=lambda x: x[1], reverse=True)
        
        target_count = max(1, int(len(sentences) * self.target_ratio))
        selected = scored_sentences[:target_count]
        
        # Restore original order
        selected_set = {s[0] for s in selected}
        compressed = [s for s in sentences if s in selected_set]
        
        compressed_text = " ".join(compressed)
        
        return CompressionResult(
            compressed_text=compressed_text,
            original_tokens=len(text) // 4,
            compressed_tokens=len(compressed_text) // 4,
            compression_ratio=len(compressed_text) / len(text) if text else 1.0,
            preserved_citations=[]
        )
    
    def _split_sentences(self, text: str) -> list[str]:
        """Split text into sentences."""
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _score_sentence(self, sentence: str, query: Optional[str] = None) -> float:
        """Score sentence importance."""
        score = 0.0
        
        # Legal term density
        legal_terms = [
            "court", "held", "holding", "plaintiff", "defendant",
            "judgment", "ruling", "statute", "precedent", "affirm"
        ]
        for term in legal_terms:
            if term.lower() in sentence.lower():
                score += 1.0
        
        # Citation presence
        if re.search(r'\d+\s+[A-Z][a-z]*\.\s*\d*d?\s+\d+', sentence):
            score += 2.0
        
        # Query relevance
        if query:
            query_terms = query.lower().split()
            for term in query_terms:
                if term in sentence.lower():
                    score += 0.5
        
        return score
