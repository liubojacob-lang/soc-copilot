"""
Vector Store Module - For RAG (Retrieval Augmented Generation)
Supports multiple backends: ChromaDB (local), Pinecone (cloud), or PostgreSQL with pgvector
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

import numpy as np

from core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class Document:
    """Document for vector storage."""

    id: str
    content: str
    metadata: dict[str, Any]
    embedding: list[float] | None = None
    created_at: datetime | None = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()


@dataclass
class SearchResult:
    """Search result from vector store."""

    document: Document
    score: float
    distance: float


class BaseVectorStore:
    """Base class for vector stores."""

    async def add_documents(self, documents: list[Document]) -> bool:
        """Add documents to vector store."""
        raise NotImplementedError

    async def search(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        filters: dict[str, Any] | None = None,
    ) -> list[SearchResult]:
        """Search for similar documents."""
        raise NotImplementedError

    async def delete(self, document_ids: list[str]) -> bool:
        """Delete documents by ID."""
        raise NotImplementedError

    async def clear(self) -> bool:
        """Clear all documents."""
        raise NotImplementedError


class ChromaDBStore(BaseVectorStore):
    """ChromaDB vector store (local, good for development)."""

    def __init__(
        self,
        collection_name: str = "soc_copilot",
        persist_directory: str = "./chroma_db",
    ):
        self.collection_name = collection_name
        self.persist_directory = persist_directory
        self._collection = None
        self._client = None

    async def _get_collection(self):
        """Lazy initialization of ChromaDB collection."""
        if self._collection is None:
            try:
                import chromadb
                from chromadb.config import Settings

                self._client = chromadb.Client(
                    Settings(
                        chroma_db_impl="duckdb+parquet",
                        persist_directory=self.persist_directory,
                    )
                )

                self._collection = self._client.get_or_create_collection(
                    name=self.collection_name, metadata={"hnsw:space": "cosine"}
                )
                logger.info(f"ChromaDB collection initialized: {self.collection_name}")
            except ImportError:
                logger.error("ChromaDB not installed. Run: pip install chromadb")
                raise
        return self._collection

    async def add_documents(self, documents: list[Document]) -> bool:
        """Add documents to ChromaDB."""
        try:
            collection = await self._get_collection()

            ids = [doc.id for doc in documents]
            texts = [doc.content for doc in documents]
            embeddings = [
                doc.embedding for doc in documents if doc.embedding is not None
            ]
            metadatas = [doc.metadata for doc in documents]

            if embeddings:
                collection.add(
                    ids=ids, documents=texts, embeddings=embeddings, metadatas=metadatas
                )
            else:
                # ChromaDB will generate embeddings automatically if not provided
                collection.add(ids=ids, documents=texts, metadatas=metadatas)

            logger.info(f"Added {len(documents)} documents to ChromaDB")
            return True
        except Exception as e:
            logger.error(f"Error adding documents to ChromaDB: {e}")
            return False

    async def search(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        filters: dict[str, Any] | None = None,
    ) -> list[SearchResult]:
        """Search ChromaDB for similar documents."""
        try:
            collection = await self._get_collection()

            results = collection.query(
                query_embeddings=[query_embedding], n_results=top_k, where=filters
            )

            search_results = []
            for i in range(len(results["ids"][0])):
                doc = Document(
                    id=results["ids"][0][i],
                    content=results["documents"][0][i],
                    metadata=results["metadatas"][0][i],
                    embedding=None,
                )
                distance = results["distances"][0][i]
                score = 1 - distance  # Convert distance to similarity score

                search_results.append(
                    SearchResult(document=doc, score=score, distance=distance)
                )

            return search_results
        except Exception as e:
            logger.error(f"Error searching ChromaDB: {e}")
            return []

    async def delete(self, document_ids: list[str]) -> bool:
        """Delete documents from ChromaDB."""
        try:
            collection = await self._get_collection()
            collection.delete(ids=document_ids)
            logger.info(f"Deleted {len(document_ids)} documents from ChromaDB")
            return True
        except Exception as e:
            logger.error(f"Error deleting documents from ChromaDB: {e}")
            return False

    async def clear(self) -> bool:
        """Clear all documents from ChromaDB."""
        try:
            collection = await self._get_collection()
            # Get all IDs and delete them
            all_docs = collection.get()
            if all_docs["ids"]:
                collection.delete(ids=all_docs["ids"])
            logger.info("Cleared all documents from ChromaDB")
            return True
        except Exception as e:
            logger.error(f"Error clearing ChromaDB: {e}")
            return False


class MemoryVectorStore(BaseVectorStore):
    """In-memory vector store (for testing/development)."""

    def __init__(self):
        self.documents: dict[str, Document] = {}

    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        a = np.array(a)
        b = np.array(b)
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

    async def add_documents(self, documents: list[Document]) -> bool:
        """Add documents to memory store."""
        for doc in documents:
            self.documents[doc.id] = doc
        logger.info(f"Added {len(documents)} documents to memory store")
        return True

    async def search(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        filters: dict[str, Any] | None = None,
    ) -> list[SearchResult]:
        """Search memory store for similar documents."""
        results = []

        for doc in self.documents.values():
            # Apply filters
            if filters:
                match = True
                for key, value in filters.items():
                    if doc.metadata.get(key) != value:
                        match = False
                        break
                if not match:
                    continue

            # Calculate similarity
            if doc.embedding:
                similarity = self._cosine_similarity(query_embedding, doc.embedding)
                distance = 1 - similarity
                results.append(
                    SearchResult(document=doc, score=similarity, distance=distance)
                )

        # Sort by score and return top_k
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:top_k]

    async def delete(self, document_ids: list[str]) -> bool:
        """Delete documents from memory store."""
        for doc_id in document_ids:
            if doc_id in self.documents:
                del self.documents[doc_id]
        return True

    async def clear(self) -> bool:
        """Clear all documents from memory store."""
        self.documents.clear()
        return True


class VectorStoreFactory:
    """Factory for creating vector stores."""

    @staticmethod
    def create_store(store_type: str = "auto", **kwargs) -> BaseVectorStore:
        """Create vector store based on type."""
        if store_type == "auto":
            # Try ChromaDB first, fallback to memory
            try:
                import chromadb

                store_type = "chromadb"
            except ImportError:
                store_type = "memory"
                logger.warning("ChromaDB not available, using memory store")

        if store_type == "chromadb":
            return ChromaDBStore(**kwargs)
        elif store_type == "memory":
            return MemoryVectorStore()
        else:
            raise ValueError(f"Unknown store type: {store_type}")


# Global vector store instance
_vector_store: BaseVectorStore | None = None


async def get_vector_store() -> BaseVectorStore:
    """Get or create global vector store instance."""
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStoreFactory.create_store()
    return _vector_store


async def initialize_vector_store():
    """Initialize vector store on application startup."""
    global _vector_store
    _vector_store = VectorStoreFactory.create_store()
    logger.info("Vector store initialized")


async def close_vector_store():
    """Close vector store on application shutdown."""
    global _vector_store
    if _vector_store:
        logger.info("Vector store closed")
        _vector_store = None
