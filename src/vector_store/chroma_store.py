"""ChromaDB vector store for legal documents."""

import hashlib
from pathlib import Path
from typing import Optional

from rich.console import Console
from tqdm import tqdm

console = Console()


class ChromaVectorStore:
    """
    ChromaDB-based vector store optimized for legal documents.
    
    Features:
    - Persistent storage for large document collections
    - Metadata filtering for legal-specific queries
    - Hybrid search combining semantic and keyword matching
    """
    
    def __init__(
        self,
        persist_directory: str = "./data/chromadb",
        collection_name: str = "legal_documents",
        embedding_model: str = "text-embedding-3-small"
    ):
        self.persist_directory = Path(persist_directory)
        self.collection_name = collection_name
        self.embedding_model = embedding_model
        
        self._client = None
        self._collection = None
        self._embedding_function = None
    
    def _ensure_initialized(self):
        """Lazy initialization of ChromaDB client."""
        if self._client is None:
            try:
                import chromadb
                from chromadb.config import Settings
            except ImportError:
                raise ImportError("chromadb is required. Install with: pip install chromadb")
            
            self.persist_directory.mkdir(parents=True, exist_ok=True)
            
            self._client = chromadb.PersistentClient(
                path=str(self.persist_directory),
                settings=Settings(anonymized_telemetry=False)
            )
            
            self._embedding_function = self._create_embedding_function()
            
            self._collection = self._client.get_or_create_collection(
                name=self.collection_name,
                embedding_function=self._embedding_function,
                metadata={"hnsw:space": "cosine"}
            )
            
            console.print(f"[green]ChromaDB initialized at {self.persist_directory}[/green]")
    
    def _create_embedding_function(self):
        """Create OpenAI embedding function."""
        try:
            from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
            import os
        except ImportError:
            raise ImportError("OpenAI embedding function requires chromadb>=0.4.0")
        
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        
        return OpenAIEmbeddingFunction(
            api_key=api_key,
            model_name=self.embedding_model
        )
    
    def add_chunks(self, chunks: list, batch_size: int = 100) -> int:
        """
        Add document chunks to the vector store.
        
        Args:
            chunks: List of DocumentChunk objects
            batch_size: Number of chunks to process at once
            
        Returns:
            Number of chunks added
        """
        self._ensure_initialized()
        
        added_count = 0
        
        for i in tqdm(range(0, len(chunks), batch_size), desc="Indexing chunks"):
            batch = chunks[i:i + batch_size]
            
            ids = []
            documents = []
            metadatas = []
            
            for chunk in batch:
                # Create unique ID based on content hash
                chunk_hash = hashlib.md5(chunk.content.encode()).hexdigest()[:12]
                chunk_id = f"{chunk.chunk_id}_{chunk_hash}"
                
                ids.append(chunk_id)
                documents.append(chunk.content)
                
                # Prepare metadata (ChromaDB only accepts str, int, float, bool)
                metadata = {
                    "document_id": chunk.document_id,
                    "section": chunk.section or "",
                    "chunk_id": chunk.chunk_id,
                }
                
                # Add document metadata
                if chunk.metadata:
                    for key, value in chunk.metadata.items():
                        if value is not None and isinstance(value, (str, int, float, bool)):
                            metadata[key] = value
                
                metadatas.append(metadata)
            
            try:
                self._collection.add(
                    ids=ids,
                    documents=documents,
                    metadatas=metadatas
                )
                added_count += len(batch)
            except Exception as e:
                console.print(f"[yellow]Warning: Error adding batch: {e}[/yellow]")
        
        console.print(f"[green]Added {added_count} chunks to vector store[/green]")
        return added_count
    
    def search(
        self,
        query: str,
        top_k: int = 10,
        filter_metadata: Optional[dict] = None,
        include_distances: bool = True
    ) -> list[dict]:
        """
        Search for relevant document chunks.
        
        Args:
            query: Search query
            top_k: Number of results to return
            filter_metadata: Optional metadata filter
            include_distances: Include similarity scores
            
        Returns:
            List of matching chunks with metadata
        """
        self._ensure_initialized()
        
        where_filter = None
        if filter_metadata:
            where_filter = filter_metadata
        
        results = self._collection.query(
            query_texts=[query],
            n_results=top_k,
            where=where_filter,
            include=["documents", "metadatas", "distances"] if include_distances else ["documents", "metadatas"]
        )
        
        # Format results
        formatted_results = []
        
        if results["documents"] and results["documents"][0]:
            for i, doc in enumerate(results["documents"][0]):
                result = {
                    "content": doc,
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                    "id": results["ids"][0][i] if results["ids"] else None
                }
                
                if include_distances and results.get("distances"):
                    # ChromaDB returns distances, convert to similarity score
                    result["similarity"] = 1 - results["distances"][0][i]
                
                formatted_results.append(result)
        
        return formatted_results
    
    def search_by_section(
        self,
        query: str,
        section: str,
        top_k: int = 5
    ) -> list[dict]:
        """Search within a specific document section."""
        return self.search(
            query=query,
            top_k=top_k,
            filter_metadata={"section": section}
        )
    
    def search_by_case(
        self,
        query: str,
        case_name: str,
        top_k: int = 10
    ) -> list[dict]:
        """Search within a specific case."""
        return self.search(
            query=query,
            top_k=top_k,
            filter_metadata={"case_name": case_name}
        )
    
    def get_collection_stats(self) -> dict:
        """Get statistics about the collection."""
        self._ensure_initialized()
        
        return {
            "collection_name": self.collection_name,
            "document_count": self._collection.count(),
            "persist_directory": str(self.persist_directory)
        }
    
    def delete_collection(self):
        """Delete the entire collection."""
        self._ensure_initialized()
        self._client.delete_collection(self.collection_name)
        self._collection = None
        console.print(f"[yellow]Collection '{self.collection_name}' deleted[/yellow]")
    
    def clear(self):
        """Clear all documents from the collection."""
        self.delete_collection()
        self._collection = self._client.get_or_create_collection(
            name=self.collection_name,
            embedding_function=self._embedding_function,
            metadata={"hnsw:space": "cosine"}
        )
