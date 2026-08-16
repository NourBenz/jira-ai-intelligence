"""PostgreSQL pgvector storage and project-isolated semantic retrieval."""

from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.database.repositories import RAGRepository
from app.rag.chunker import RAGChunk


@dataclass(frozen=True)
class VectorSearchResult:
    chunk_id: str
    text: str
    metadata: dict[str, Any]
    similarity: float


class PgVectorStore:
    """Validate vectors and delegate persistent operations to PostgreSQL."""

    def __init__(self, session: Session, dimensions: int = 768) -> None:
        if dimensions <= 0:
            raise ValueError("dimensions must be greater than zero")
        self.session = session
        self.dimensions = dimensions
        self.repository = RAGRepository(session)

    def index(
        self,
        project_key: str,
        chunks: list[RAGChunk],
        embeddings: list[list[float]],
    ) -> int:
        self._require_postgresql()
        self._validate_vectors(embeddings)
        return self.repository.synchronize_chunks(project_key, chunks, embeddings)

    def search(
        self,
        project_key: str,
        query_embedding: list[float],
        top_k: int = 5,
    ) -> list[VectorSearchResult]:
        self._require_postgresql()
        if not 1 <= top_k <= 50:
            raise ValueError("top_k must be between 1 and 50")
        self._validate_vectors([query_embedding])
        return [
            VectorSearchResult(
                chunk_id=entity.chunk_id,
                text=entity.text,
                metadata=entity.source_metadata,
                similarity=round(1.0 - distance, 6),
            )
            for entity, distance in self.repository.search(project_key, query_embedding, top_k)
        ]

    def _validate_vectors(self, vectors: list[list[float]]) -> None:
        if any(len(vector) != self.dimensions for vector in vectors):
            raise ValueError(f"Every embedding must contain {self.dimensions} dimensions.")

    def _require_postgresql(self) -> None:
        bind = self.session.get_bind()
        if bind.dialect.name != "postgresql":
            raise RuntimeError("RAG vector storage requires PostgreSQL with pgvector.")
