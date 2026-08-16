"""Store issue membership for synchronized sprints."""

from alembic import op
import sqlalchemy as sa


revision = "20260713_02"
down_revision = "20260712_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sprint_issues",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("sprint_id", sa.Integer(), nullable=False),
        sa.Column("issue_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["issue_id"], ["issues.id"],
            name="fk_sprint_issues_issue_id_issues",
        ),
        sa.ForeignKeyConstraint(
            ["sprint_id"], ["sprints.id"],
            name="fk_sprint_issues_sprint_id_sprints",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_sprint_issues"),
        sa.UniqueConstraint(
            "sprint_id", "issue_id",
            name="uq_sprint_issues_sprint_id",
        ),
    )
    op.create_index("ix_sprint_issues_sprint_id", "sprint_issues", ["sprint_id"])
    op.create_index("ix_sprint_issues_issue_id", "sprint_issues", ["issue_id"])


def downgrade() -> None:
    op.drop_table("sprint_issues")
