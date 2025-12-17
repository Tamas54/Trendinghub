"""
RAG Style Learning Module for TrendMaster
Uses ChromaDB for vector storage and sentence-transformers for embeddings
"""
import os
import chromadb
from chromadb.config import Settings
from typing import List, Dict, Optional
import hashlib
import json

# Lazy load sentence-transformers to avoid slow startup
_embedding_model = None


def get_embedding_model():
    """Lazy load the embedding model."""
    global _embedding_model
    if _embedding_model is None:
        # Force CPU mode - disable CUDA completely (for Railway/serverless)
        import os
        os.environ['CUDA_VISIBLE_DEVICES'] = ''

        import torch
        torch.set_default_device('cpu')

        from sentence_transformers import SentenceTransformer
        # Use a multilingual model that supports Hungarian - explicitly on CPU
        _embedding_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2', device='cpu')
        print("✅ Embedding model loaded: paraphrase-multilingual-MiniLM-L12-v2 (CPU)")
    return _embedding_model


class RAGStyleStore:
    """
    ChromaDB-based RAG store for learning influencer writing styles.
    Stores text chunks with embeddings for similarity search.
    """

    def __init__(self, persist_dir: str = None):
        """Initialize the RAG store with optional persistence."""
        if persist_dir is None:
            # Default to a directory in the project
            persist_dir = os.path.join(os.path.dirname(__file__), 'chroma_db')

        os.makedirs(persist_dir, exist_ok=True)

        self.client = chromadb.PersistentClient(
            path=persist_dir,
            settings=Settings(anonymized_telemetry=False)
        )

        # Collection for style samples
        self.collection = self.client.get_or_create_collection(
            name="influencer_styles",
            metadata={"description": "Influencer writing style samples"}
        )

        print(f"✅ RAG Store initialized at {persist_dir}")
        print(f"   Collection size: {self.collection.count()} documents")

    def chunk_text(self, text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
        """
        Split text into overlapping chunks for embedding.

        Args:
            text: The text to chunk
            chunk_size: Target size of each chunk in characters
            overlap: Number of characters to overlap between chunks

        Returns:
            List of text chunks
        """
        if len(text) <= chunk_size:
            return [text]

        chunks = []
        start = 0

        while start < len(text):
            end = start + chunk_size

            # Try to break at sentence boundary
            if end < len(text):
                # Look for sentence end within the last 20% of chunk
                search_start = max(start, end - int(chunk_size * 0.2))
                last_period = text.rfind('.', search_start, end)
                last_newline = text.rfind('\n', search_start, end)

                best_break = max(last_period, last_newline)
                if best_break > start:
                    end = best_break + 1

            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)

            start = end - overlap

        return chunks

    def add_style_sample(self, text: str, source_name: str, style_name: str = "default") -> int:
        """
        Add a writing style sample to the store.

        Args:
            text: The text content (post, article, etc.)
            source_name: Name/identifier of the source (e.g., "influencer_x", "book_title")
            style_name: Style category (e.g., "formal", "casual", "humorous")

        Returns:
            Number of chunks added
        """
        chunks = self.chunk_text(text)

        if not chunks:
            return 0

        # Generate embeddings
        model = get_embedding_model()
        embeddings = model.encode(chunks).tolist()

        # Generate unique IDs based on content hash
        ids = []
        for i, chunk in enumerate(chunks):
            chunk_hash = hashlib.md5(chunk.encode()).hexdigest()[:12]
            ids.append(f"{source_name}_{style_name}_{chunk_hash}_{i}")

        # Prepare metadata
        metadatas = [
            {
                "source_name": source_name,
                "style_name": style_name,
                "chunk_index": i,
                "total_chunks": len(chunks)
            }
            for i in range(len(chunks))
        ]

        # Add to collection (upsert to handle duplicates)
        self.collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=chunks,
            metadatas=metadatas
        )

        print(f"✅ Added {len(chunks)} chunks from '{source_name}' (style: {style_name})")
        return len(chunks)

    def query_style(self, query_text: str, n_results: int = 5,
                    source_filter: str = None, style_filter: str = None) -> List[Dict]:
        """
        Query the store for similar style samples.

        Args:
            query_text: Text to find similar styles for
            n_results: Number of results to return
            source_filter: Filter by source name (optional)
            style_filter: Filter by style name (optional)

        Returns:
            List of matching documents with metadata
        """
        model = get_embedding_model()
        query_embedding = model.encode([query_text]).tolist()

        # Build where clause for filtering
        where = None
        if source_filter and style_filter:
            where = {
                "$and": [
                    {"source_name": source_filter},
                    {"style_name": style_filter}
                ]
            }
        elif source_filter:
            where = {"source_name": source_filter}
        elif style_filter:
            where = {"style_name": style_filter}

        results = self.collection.query(
            query_embeddings=query_embedding,
            n_results=n_results,
            where=where,
            include=["documents", "metadatas", "distances"]
        )

        # Format results
        formatted = []
        if results['documents'] and results['documents'][0]:
            for i, doc in enumerate(results['documents'][0]):
                formatted.append({
                    "text": doc,
                    "metadata": results['metadatas'][0][i] if results['metadatas'] else {},
                    "distance": results['distances'][0][i] if results['distances'] else 0
                })

        return formatted

    def get_style_context(self, query_text: str, max_tokens: int = 1000) -> str:
        """
        Get style context for prompt augmentation.

        Args:
            query_text: The topic/text to generate style context for
            max_tokens: Approximate maximum characters for context

        Returns:
            Formatted string with style examples for prompt injection
        """
        results = self.query_style(query_text, n_results=3)

        if not results:
            return ""

        context_parts = []
        total_chars = 0

        for result in results:
            text = result['text']
            source = result['metadata'].get('source_name', 'unknown')

            if total_chars + len(text) > max_tokens:
                # Truncate if needed
                remaining = max_tokens - total_chars
                if remaining > 100:
                    text = text[:remaining] + "..."
                else:
                    break

            context_parts.append(f"[Példa - {source}]:\n{text}")
            total_chars += len(text)

        if not context_parts:
            return ""

        return "STÍLUS PÉLDÁK (használd referenciának):\n" + "\n\n".join(context_parts)

    def list_sources(self) -> List[Dict]:
        """List all unique sources in the store."""
        # Get all documents with metadata
        all_data = self.collection.get(include=["metadatas"])

        sources = {}
        if all_data['metadatas']:
            for meta in all_data['metadatas']:
                source = meta.get('source_name', 'unknown')
                style = meta.get('style_name', 'default')

                if source not in sources:
                    sources[source] = {'source_name': source, 'styles': set(), 'chunk_count': 0}

                sources[source]['styles'].add(style)
                sources[source]['chunk_count'] += 1

        # Convert sets to lists for JSON serialization
        result = []
        for source_data in sources.values():
            source_data['styles'] = list(source_data['styles'])
            result.append(source_data)

        return result

    def delete_source(self, source_name: str) -> int:
        """Delete all chunks from a specific source."""
        # Get IDs to delete
        all_data = self.collection.get(
            where={"source_name": source_name},
            include=["metadatas"]
        )

        if not all_data['ids']:
            return 0

        self.collection.delete(ids=all_data['ids'])
        print(f"✅ Deleted {len(all_data['ids'])} chunks from '{source_name}'")
        return len(all_data['ids'])

    def get_stats(self) -> Dict:
        """Get statistics about the store."""
        sources = self.list_sources()

        return {
            "total_documents": self.collection.count(),
            "unique_sources": len(sources),
            "sources": sources
        }


# Global instance
_rag_store = None


def get_rag_store() -> RAGStyleStore:
    """Get or create the global RAG store instance."""
    global _rag_store
    if _rag_store is None:
        _rag_store = RAGStyleStore()
    return _rag_store
