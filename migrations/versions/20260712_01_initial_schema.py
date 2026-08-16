"""Create initial Jira persistence schema."""

from alembic import op
import sqlalchemy as sa


revision = "20260712_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("jira_id", sa.String(100), nullable=False),
        sa.Column("key", sa.String(50), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("synchronized_at", sa.DateTime(timezone=True)),
        sa.PrimaryKeyConstraint("id", name="pk_projects"),
        sa.UniqueConstraint("jira_id", name="uq_projects_jira_id"),
        sa.UniqueConstraint("key", name="uq_projects_key"),
    )
    op.create_index("ix_projects_jira_id", "projects", ["jira_id"])
    op.create_index("ix_projects_key", "projects", ["key"])

    op.create_table(
        "issues",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("jira_id", sa.String(100), nullable=False),
        sa.Column("key", sa.String(50), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("summary", sa.String(500)),
        sa.Column("description", sa.JSON()),
        sa.Column("status", sa.String(100)),
        sa.Column("status_category", sa.String(100)),
        sa.Column("priority", sa.String(100)),
        sa.Column("issue_type", sa.String(100)),
        sa.Column("assignee", sa.String(255)),
        sa.Column("reporter", sa.String(255)),
        sa.Column("created_at", sa.DateTime(timezone=True)),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
        sa.Column("resolution_date", sa.DateTime(timezone=True)),
        sa.Column("due_date", sa.Date()),
        sa.Column("story_points", sa.Float()),
        sa.Column("labels", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], name="fk_issues_project_id_projects"),
        sa.PrimaryKeyConstraint("id", name="pk_issues"),
        sa.UniqueConstraint("jira_id", name="uq_issues_jira_id"),
        sa.UniqueConstraint("key", name="uq_issues_key"),
    )
    for column in ("jira_id", "key", "project_id", "status", "priority", "issue_type", "assignee", "updated_at"):
        op.create_index(f"ix_issues_{column}", "issues", [column])

    op.create_table(
        "sprints",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("jira_id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer()),
        sa.Column("board_id", sa.Integer()),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("state", sa.String(50), nullable=False),
        sa.Column("start_date", sa.DateTime(timezone=True)),
        sa.Column("end_date", sa.DateTime(timezone=True)),
        sa.Column("complete_date", sa.DateTime(timezone=True)),
        sa.Column("goal", sa.Text()),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], name="fk_sprints_project_id_projects"),
        sa.PrimaryKeyConstraint("id", name="pk_sprints"),
        sa.UniqueConstraint("jira_id", name="uq_sprints_jira_id"),
    )
    for column in ("jira_id", "project_id", "board_id", "state"):
        op.create_index(f"ix_sprints_{column}", "sprints", [column])

    op.create_table(
        "changelogs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("issue_id", sa.Integer(), nullable=False),
        sa.Column("jira_history_id", sa.String(100), nullable=False),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("author_name", sa.String(255)),
        sa.Column("items", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["issue_id"], ["issues.id"], name="fk_changelogs_issue_id_issues"),
        sa.PrimaryKeyConstraint("id", name="pk_changelogs"),
        sa.UniqueConstraint("issue_id", "jira_history_id", name="uq_changelogs_issue_id"),
    )
    op.create_index("ix_changelogs_issue_id", "changelogs", ["issue_id"])
    op.create_index("ix_changelogs_changed_at", "changelogs", ["changed_at"])

    op.create_table(
        "sync_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_key", sa.String(50), nullable=False),
        sa.Column("mode", sa.String(30), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("projects_processed", sa.Integer(), nullable=False),
        sa.Column("issues_processed", sa.Integer(), nullable=False),
        sa.Column("sprints_processed", sa.Integer(), nullable=False),
        sa.Column("changelogs_processed", sa.Integer(), nullable=False),
        sa.Column("error_message", sa.String(500)),
        sa.PrimaryKeyConstraint("id", name="pk_sync_runs"),
    )
    op.create_index("ix_sync_runs_project_key", "sync_runs", ["project_key"])
    op.create_index("ix_sync_runs_status", "sync_runs", ["status"])


def downgrade() -> None:
    op.drop_table("sync_runs")
    op.drop_table("changelogs")
    op.drop_table("sprints")
    op.drop_table("issues")
    op.drop_table("projects")
