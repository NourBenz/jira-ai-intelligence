"""Persist Jira comments for RAG evidence."""

from alembic import op
import sqlalchemy as sa


revision = "20260714_04"
down_revision = "20260713_03"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "comments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("issue_id", sa.Integer(), nullable=False),
        sa.Column("jira_id", sa.String(100), nullable=False),
        sa.Column("author_name", sa.String(255)),
        sa.Column("body", sa.JSON()),
        sa.Column("created_at", sa.DateTime(timezone=True)),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["issue_id"], ["issues.id"]),
        sa.PrimaryKeyConstraint("id", name="pk_comments"),
        sa.UniqueConstraint("issue_id", "jira_id", name="uq_comments_issue_jira"),
    )
    op.create_index("ix_comments_issue_id", "comments", ["issue_id"])
    op.create_index("ix_comments_jira_id", "comments", ["jira_id"])
    op.add_column(
        "sync_runs",
        sa.Column(
            "comments_processed",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )


def downgrade() -> None:
    op.drop_column("sync_runs", "comments_processed")
    op.drop_table("comments")
