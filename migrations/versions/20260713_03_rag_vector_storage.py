"""Add project-scoped pgvector storage for RAG chunks."""

from alembic import op
from pgvector.sqlalchemy import Vector
import sqlalchemy as sa


revision = "20260713_03"
down_revision = "20260713_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "rag_chunks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("chunk_id", sa.String(64), nullable=False),
        sa.Column("project_key", sa.String(50), nullable=False),
        sa.Column("issue_key", sa.String(50), nullable=False),
        sa.Column("content_type", sa.String(50), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("source_metadata", sa.JSON(), nullable=False),
        sa.Column("source_updated_at", sa.DateTime(timezone=True)),
        sa.Column("embedded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("embedding", Vector(768), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_rag_chunks"),
        sa.UniqueConstraint("chunk_id", name="uq_rag_chunks_chunk_id"),
    )
    op.create_index("ix_rag_chunks_chunk_id", "rag_chunks", ["chunk_id"])
    op.create_index("ix_rag_chunks_project_key", "rag_chunks", ["project_key"])
    op.create_index("ix_rag_chunks_issue_key", "rag_chunks", ["issue_key"])
    op.create_index("ix_rag_chunks_content_type", "rag_chunks", ["content_type"])
    op.create_index("ix_rag_chunks_content_hash", "rag_chunks", ["content_hash"])


def downgrade() -> None:
    op.drop_table("rag_chunks")
