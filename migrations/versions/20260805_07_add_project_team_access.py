"""Add Scrum teams and project-scoped access assignments."""

from alembic import op
import sqlalchemy as sa


revision = "20260805_07"
down_revision = "20260803_06"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "teams",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("name"),
    )
    op.create_index("ix_teams_name", "teams", ["name"], unique=True)
    op.create_index("ix_teams_is_active", "teams", ["is_active"])

    with op.batch_alter_table("projects") as batch:
        batch.add_column(sa.Column("owning_team_id", sa.Integer(), nullable=True))
        batch.create_index("ix_projects_owning_team_id", ["owning_team_id"])
        batch.create_foreign_key(
            "fk_projects_owning_team_id_teams",
            "teams",
            ["owning_team_id"],
            ["id"],
            ondelete="SET NULL",
        )

    op.create_table(
        "team_memberships",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("team_id", sa.Integer(), nullable=False),
        sa.Column("scrum_role", sa.String(50), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "team_id"),
    )
    op.create_index("ix_team_memberships_user_id", "team_memberships", ["user_id"])
    op.create_index("ix_team_memberships_team_id", "team_memberships", ["team_id"])
    op.create_index("ix_team_memberships_is_active", "team_memberships", ["is_active"])

    op.create_table(
        "project_administrators",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("granted_by_user_id", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("granted_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["granted_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("user_id", "project_id"),
    )
    op.create_index("ix_project_administrators_user_id", "project_administrators", ["user_id"])
    op.create_index(
        "ix_project_administrators_project_id", "project_administrators", ["project_id"]
    )
    op.create_index(
        "ix_project_administrators_is_active", "project_administrators", ["is_active"]
    )


def downgrade() -> None:
    op.drop_table("project_administrators")
    op.drop_table("team_memberships")
    with op.batch_alter_table("projects") as batch:
        batch.drop_constraint("fk_projects_owning_team_id_teams", type_="foreignkey")
        batch.drop_index("ix_projects_owning_team_id")
        batch.drop_column("owning_team_id")
    op.drop_table("teams")
