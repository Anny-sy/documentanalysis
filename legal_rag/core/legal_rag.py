"""Legal RAG Engine - Core retrieval-augmented generation system."""

from typing import Optional
from dataclasses import dataclass, field

from rich.console import Console

console = Console()


@dataclass
class RAGResponse:
    """Response from the RAG system."""
    
    answer: str
    sources: list[dict]
    compressed_context: str
    token_stats: dict
    query: str
    metadata: dict = field(default_factory=dict)


class LegalRAGEngine:
    """
    Legal document RAG engine with compressed prompts.
    
    This engine combines:
    - Semantic search via ChromaDB
    - LLMLingua prompt compression
    - OpenAI GPT-4 for generation
    
    Optimized for handling 1000+ page legal documents while
    minimizing token costs through intelligent compression.
    """
    
    SYSTEM_PROMPT = """You are an expert legal analyst assistant. Your role is to provide accurate, well-reasoned analysis of legal documents, case law, and statutes.

Guidelines:
1. Base your answers ONLY on the provided context
2. Cite specific cases, statutes, or document sections when possible
3. Acknowledge when information is incomplete or unclear
4. Use precise legal terminology
5. Structure complex answers with clear headings
6. Distinguish between holdings, dicta, and your analysis

If the context doesn't contain sufficient information to answer the question, clearly state that and explain what additional information would be needed."""
    
    def __init__(
        self,
        vector_store=None,
        compressor=None,
        openai_model: str = "gpt-4-turbo-preview",
        top_k: int = 10,
        compression_enabled: bool = True,
        max_context_tokens: int = 8000
    ):
        """
        Initialize the Legal RAG Engine.
        
        Args:
            vector_store: ChromaVectorStore instance
            compressor: LLMLinguaCompressor instance
            openai_model: OpenAI model to use
            top_k: Number of chunks to retrieve
            compression_enabled: Whether to compress retrieved context
            max_context_tokens: Maximum tokens for context
        """
        self.vector_store = vector_store
        self.compressor = compressor
        self.openai_model = openai_model
        self.top_k = top_k
        self.compression_enabled = compression_enabled
        self.max_context_tokens = max_context_tokens
        
        self._openai_client = None
    
    def _get_openai_client(self):
        """Get or create OpenAI client."""
        if self._openai_client is None:
            try:
                from openai import OpenAI
                import os
            except ImportError:
                raise ImportError("openai is required. Install with: pip install openai")
            
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY environment variable is required")
            
            self._openai_client = OpenAI(api_key=api_key)
        
        return self._openai_client
    
    def query(
        self,
        question: str,
        filter_metadata: Optional[dict] = None,
        include_sources: bool = True
    ) -> RAGResponse:
        """
        Query the legal document corpus.
        
        Args:
            question: User's legal question
            filter_metadata: Optional filters (e.g., case_name, court)
            include_sources: Whether to include source citations
            
        Returns:
            RAGResponse with answer and metadata
        """
        if not self.vector_store:
            raise ValueError("Vector store not initialized")
        
        # Step 1: Retrieve relevant chunks
        console.print(f"[blue]Retrieving top {self.top_k} relevant chunks...[/blue]")
        chunks = self.vector_store.search(
            query=question,
            top_k=self.top_k,
            filter_metadata=filter_metadata
        )
        
        if not chunks:
            return RAGResponse(
                answer="No relevant documents found for your query.",
                sources=[],
                compressed_context="",
                token_stats={"original": 0, "compressed": 0, "savings": 0},
                query=question
            )
        
        # Step 2: Prepare context
        original_context = self._format_context(chunks)
        original_tokens = len(original_context) // 4
        
        # Step 3: Compress context if enabled
        if self.compression_enabled and self.compressor:
            console.print("[blue]Compressing context with LLMLingua...[/blue]")
            compression_result = self.compressor.compress(
                text=original_context,
                query=question,
                preserve_citations=True
            )
            context = compression_result.compressed_text
            compressed_tokens = compression_result.compressed_tokens
            
            console.print(
                f"[green]Compression: {original_tokens} -> {compressed_tokens} tokens "
                f"({compression_result.compression_ratio:.1%})[/green]"
            )
        else:
            context = original_context
            compressed_tokens = original_tokens
        
        # Step 4: Generate response
        console.print("[blue]Generating response...[/blue]")
        answer = self._generate_response(question, context)
        
        # Step 5: Prepare response
        token_stats = {
            "original": original_tokens,
            "compressed": compressed_tokens,
            "savings": original_tokens - compressed_tokens,
            "savings_percent": ((original_tokens - compressed_tokens) / original_tokens * 100) if original_tokens > 0 else 0
        }
        
        return RAGResponse(
            answer=answer,
            sources=chunks if include_sources else [],
            compressed_context=context,
            token_stats=token_stats,
            query=question
        )
    
    def _format_context(self, chunks: list[dict]) -> str:
        """Format retrieved chunks into context string."""
        context_parts = []
        
        for i, chunk in enumerate(chunks, 1):
            metadata = chunk.get("metadata", {})
            source_info = []
            
            if metadata.get("case_name"):
                source_info.append(f"Case: {metadata['case_name']}")
            if metadata.get("court"):
                source_info.append(f"Court: {metadata['court']}")
            if metadata.get("section"):
                source_info.append(f"Section: {metadata['section']}")
            if metadata.get("filename"):
                source_info.append(f"File: {metadata['filename']}")
            
            header = f"[Document {i}]"
            if source_info:
                header += f" ({'; '.join(source_info)})"
            
            context_parts.append(f"{header}\n{chunk['content']}")
        
        return "\n\n---\n\n".join(context_parts)
    
    def _generate_response(self, question: str, context: str) -> str:
        """Generate response using OpenAI."""
        client = self._get_openai_client()
        
        user_message = f"""Based on the following legal documents and context, please answer this question:

QUESTION: {question}

CONTEXT:
{context}

Please provide a comprehensive answer based on the context above. Cite specific sources when possible."""
        
        response = client.chat.completions.create(
            model=self.openai_model,
            messages=[
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": user_message}
            ],
            temperature=0.1,
            max_tokens=2000
        )
        
        return response.choices[0].message.content
    
    def analyze_case(self, case_name: str) -> RAGResponse:
        """Analyze a specific case in the corpus."""
        question = f"""Provide a comprehensive analysis of {case_name} including:
1. Key facts of the case
2. Legal issues presented
3. Court's holding and reasoning
4. Significance and precedential value
5. Any notable dissents or concurrences"""
        
        return self.query(
            question=question,
            filter_metadata={"case_name": case_name} if case_name else None
        )
    
    def compare_cases(self, case1: str, case2: str) -> RAGResponse:
        """Compare two cases in the corpus."""
        question = f"""Compare and contrast {case1} and {case2}:
1. How do the facts differ?
2. What legal principles does each case establish?
3. How do the holdings relate to each other?
4. Are there any conflicts or tensions between the cases?
5. Which case would be more applicable in different scenarios?"""
        
        return self.query(question=question)
    
    def find_precedents(self, legal_issue: str) -> RAGResponse:
        """Find relevant precedents for a legal issue."""
        question = f"""Find and analyze relevant case law precedents for the following legal issue:

{legal_issue}

For each relevant precedent:
1. Cite the case name and citation
2. Explain how it relates to this issue
3. Note the holding and key reasoning
4. Assess its current validity and strength as precedent"""
        
        return self.query(question=question)
