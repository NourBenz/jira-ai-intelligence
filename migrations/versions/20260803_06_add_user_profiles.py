"""Add optional human profile fields to prototype users."""

from alembic import op
import sqlalchemy as sa


revision = "20260803_06"
down_revision = "20260723_05"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("first_name", sa.String(100), nullable=True))
    op.add_column("users", sa.Column("last_name", sa.String(100), nullable=True))
    op.add_column("users", sa.Column("email", sa.String(254), nullable=True))
    op.create_index("ix_users_email", "users", ["email"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_users_email", table_name="users")
    op.drop_column("users", "email")
    op.drop_column("users", "last_name")
    op.drop_column("users", "first_name")
