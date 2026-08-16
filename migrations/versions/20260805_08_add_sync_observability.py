"""Persist Jira update checks and issue-level synchronization details."""

from alembic import op
import sqlalchemy as sa


revision = "20260805_08"
down_revision = "20260805_07"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("projects") as batch:
        batch.add_column(sa.Column("jira_checked_at", sa.DateTime(timezone=True)))
        batch.add_column(sa.Column("jira_latest_issue_key", sa.String(50)))
        batch.add_column(sa.Column("jira_latest_updated_at", sa.DateTime(timezone=True)))
        batch.add_column(
            sa.Column(
                "jira_updates_available",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )
        batch.add_column(sa.Column("jira_update_check_error", sa.String(255)))
        batch.create_index("ix_projects_jira_updates_available", ["jira_updates_available"])

    op.create_table(
        "sync_changes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("sync_run_id", sa.Integer(), nullable=False),
        sa.Column("issue_key", sa.String(50), nullable=False),
        sa.Column("change_type", sa.String(30), nullable=False),
        sa.Column("changed_fields", sa.JSON(), nullable=False),
        sa.Column("before_values", sa.JSON(), nullable=False),
        sa.Column("after_values", sa.JSON(), nullable=False),
        sa.Column("changelogs_inspected", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("comments_inspected", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["sync_run_id"], ["sync_runs.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("sync_run_id", "issue_key"),
    )
    op.create_index("ix_sync_changes_sync_run_id", "sync_changes", ["sync_run_id"])
    op.create_index("ix_sync_changes_issue_key", "sync_changes", ["issue_key"])
    op.create_index("ix_sync_changes_change_type", "sync_changes", ["change_type"])


def downgrade() -> None:
    op.drop_table("sync_changes")
    with op.batch_alter_table("projects") as batch:
        batch.drop_index("ix_projects_jira_updates_available")
        batch.drop_column("jira_update_check_error")
        batch.drop_column("jira_updates_available")
        batch.drop_column("jira_latest_updated_at")
        batch.drop_column("jira_latest_issue_key")
        batch.drop_column("jira_checked_at")
