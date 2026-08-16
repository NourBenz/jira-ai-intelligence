import os

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database.session import create_database_engine
from app.rag.chunker import RAGChunk
from app.rag.vector_store import PgVectorStore


def test_postgres_connection_when_configured():
    database_url = os.getenv("POSTGRES_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("Set POSTGRES_TEST_DATABASE_URL for the PostgreSQL smoke test")

    engine = create_database_engine(database_url)
    try:
        with engine.connect() as connection:
            assert connection.scalar(text("SELECT 1")) == 1
            assert connection.dialect.name == "postgresql"
    finally:
        engine.dispose()


def test_pgvector_search_is_idempotent_and_project_scoped():
    database_url = os.getenv("POSTGRES_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("Set POSTGRES_TEST_DATABASE_URL for the pgvector test")

    engine = create_database_engine(database_url)
    try:
        with engine.connect() as connection:
            assert (
                connection.scalar(text("SELECT extname FROM pg_extension WHERE extname = 'vector'"))
                == "vector"
            )

        with Session(engine) as session:
            store = PgVectorStore(session, dimensions=768)
            primary = [1.0] + [0.0] * 767
            secondary = [0.0, 1.0] + [0.0] * 766
            chunks = [
                RAGChunk(
                    id="a" * 64,
                    text="Users cannot sign in",
                    metadata={
                        "project_key": "_RAG_TEST_A",
                        "issue_key": "A-1",
                        "content_type": "summary",
                        "chunk_index": 0,
                        "source_updated_at": None,
                    },
                ),
                RAGChunk(
                    id="b" * 64,
                    text="Sprint reporting problem",
                    metadata={
                        "project_key": "_RAG_TEST_A",
                        "issue_key": "A-2",
                        "content_type": "summary",
                        "chunk_index": 0,
                        "source_updated_at": None,
                    },
                ),
            ]
            other_project_chunk = RAGChunk(
                id="c" * 64,
                text="Authentication failure in another project",
                metadata={
                    "project_key": "_RAG_TEST_B",
                    "issue_key": "B-1",
                    "content_type": "summary",
                    "chunk_index": 0,
                    "source_updated_at": None,
                },
            )

            assert store.index("_RAG_TEST_A", chunks, [primary, secondary]) == 2
            assert store.index("_RAG_TEST_A", chunks, [primary, secondary]) == 2
            store.index("_RAG_TEST_B", [other_project_chunk], [primary])

            results = store.search("_RAG_TEST_A", primary, top_k=5)

            assert [result.metadata["issue_key"] for result in results] == ["A-1", "A-2"]
            assert all(result.metadata["project_key"] == "_RAG_TEST_A" for result in results)
            session.rollback()
    finally:
        engine.dispose()
