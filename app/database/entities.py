from datetime import date, datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class ProjectEntity(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    jira_id: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    key: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    synchronized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    jira_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    jira_latest_issue_key: Mapped[str | None] = mapped_column(String(50))
    jira_latest_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    jira_updates_available: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    jira_update_check_error: Mapped[str | None] = mapped_column(String(255))
    owning_team_id: Mapped[int | None] = mapped_column(
        ForeignKey("teams.id", ondelete="SET NULL"),
        index=True,
    )

    issues: Mapped[list["IssueEntity"]] = relationship(back_populates="project")
    sprints: Mapped[list["SprintEntity"]] = relationship(back_populates="project")
    owning_team: Mapped["TeamEntity | None"] = relationship(back_populates="projects")
    administrator_links: Mapped[list["ProjectAdministratorEntity"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
    )


class IssueEntity(Base):
    __tablename__ = "issues"

    id: Mapped[int] = mapped_column(primary_key=True)
    jira_id: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    key: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    summary: Mapped[str | None] = mapped_column(String(500))
    description: Mapped[dict[str, Any] | str | None] = mapped_column(JSON)
    status: Mapped[str | None] = mapped_column(String(100), index=True)
    status_category: Mapped[str | None] = mapped_column(String(100))
    priority: Mapped[str | None] = mapped_column(String(100), index=True)
    issue_type: Mapped[str | None] = mapped_column(String(100), index=True)
    assignee: Mapped[str | None] = mapped_column(String(255), index=True)
    reporter: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    resolution_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    due_date: Mapped[date | None] = mapped_column(Date)
    story_points: Mapped[float | None] = mapped_column(Float)
    labels: Mapped[list[str]] = mapped_column(JSON, default=list)

    project: Mapped[ProjectEntity] = relationship(back_populates="issues")
    changelogs: Mapped[list["ChangelogEntity"]] = relationship(
        back_populates="issue", cascade="all, delete-orphan"
    )
    comments: Mapped[list["CommentEntity"]] = relationship(
        back_populates="issue", cascade="all, delete-orphan"
    )


class SprintEntity(Base):
    __tablename__ = "sprints"

    id: Mapped[int] = mapped_column(primary_key=True)
    jira_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id"), index=True)
    board_id: Mapped[int | None] = mapped_column(Integer, index=True)
    name: Mapped[str] = mapped_column(String(255))
    state: Mapped[str] = mapped_column(String(50), index=True)
    start_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    end_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    complete_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    goal: Mapped[str | None] = mapped_column(Text)

    project: Mapped[ProjectEntity | None] = relationship(back_populates="sprints")
    issue_links: Mapped[list["SprintIssueEntity"]] = relationship(
        back_populates="sprint", cascade="all, delete-orphan"
    )


class SprintIssueEntity(Base):
    __tablename__ = "sprint_issues"
    __table_args__ = (UniqueConstraint("sprint_id", "issue_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    sprint_id: Mapped[int] = mapped_column(ForeignKey("sprints.id"), index=True)
    issue_id: Mapped[int] = mapped_column(ForeignKey("issues.id"), index=True)

    sprint: Mapped[SprintEntity] = relationship(back_populates="issue_links")
    issue: Mapped[IssueEntity] = relationship()


class ChangelogEntity(Base):
    __tablename__ = "changelogs"
    __table_args__ = (UniqueConstraint("issue_id", "jira_history_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    issue_id: Mapped[int] = mapped_column(ForeignKey("issues.id"), index=True)
    jira_history_id: Mapped[str] = mapped_column(String(100))
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    author_name: Mapped[str | None] = mapped_column(String(255))
    items: Mapped[list[dict[str, Any]]] = mapped_column(JSON)

    issue: Mapped[IssueEntity] = relationship(back_populates="changelogs")


class CommentEntity(Base):
    """A Jira comment persisted for traceable semantic retrieval."""

    __tablename__ = "comments"
    __table_args__ = (UniqueConstraint("issue_id", "jira_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    issue_id: Mapped[int] = mapped_column(ForeignKey("issues.id"), index=True)
    jira_id: Mapped[str] = mapped_column(String(100), index=True)
    author_name: Mapped[str | None] = mapped_column(String(255))
    body: Mapped[dict[str, Any] | str | None] = mapped_column(JSON)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    issue: Mapped[IssueEntity] = relationship(back_populates="comments")


class SyncRunEntity(Base):
    __tablename__ = "sync_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_key: Mapped[str] = mapped_column(String(50), index=True)
    mode: Mapped[str] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(30), index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    projects_processed: Mapped[int] = mapped_column(Integer, default=0)
    issues_processed: Mapped[int] = mapped_column(Integer, default=0)
    sprints_processed: Mapped[int] = mapped_column(Integer, default=0)
    changelogs_processed: Mapped[int] = mapped_column(Integer, default=0)
    comments_processed: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(String(500))
    changes: Mapped[list["SyncChangeEntity"]] = relationship(
        back_populates="sync_run",
        cascade="all, delete-orphan",
    )


class SyncChangeEntity(Base):
    """One issue snapshot inspected by a synchronization run."""

    __tablename__ = "sync_changes"
    __table_args__ = (UniqueConstraint("sync_run_id", "issue_key"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    sync_run_id: Mapped[int] = mapped_column(
        ForeignKey("sync_runs.id", ondelete="CASCADE"), index=True
    )
    issue_key: Mapped[str] = mapped_column(String(50), index=True)
    change_type: Mapped[str] = mapped_column(String(30), index=True)
    changed_fields: Mapped[list[str]] = mapped_column(JSON, default=list)
    before_values: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    after_values: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    changelogs_inspected: Mapped[int] = mapped_column(Integer, default=0)
    comments_inspected: Mapped[int] = mapped_column(Integer, default=0)

    sync_run: Mapped[SyncRunEntity] = relationship(back_populates="changes")


class RAGChunkEntity(Base):
    """Persistent, project-scoped Jira text and its semantic embedding."""

    __tablename__ = "rag_chunks"

    id: Mapped[int] = mapped_column(primary_key=True)
    chunk_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    project_key: Mapped[str] = mapped_column(String(50), index=True)
    issue_key: Mapped[str] = mapped_column(String(50), index=True)
    content_type: Mapped[str] = mapped_column(String(50), index=True)
    chunk_index: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(String(64), index=True)
    source_metadata: Mapped[dict[str, Any]] = mapped_column(JSON)
    source_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    embedded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    embedding: Mapped[list[float]] = mapped_column(Vector(768))


class UserEntity(Base):
    """A local prototype identity used for JWT access control."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    first_name: Mapped[str | None] = mapped_column(String(100))
    last_name: Mapped[str | None] = mapped_column(String(100))
    email: Mapped[str | None] = mapped_column(String(254), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    team_links: Mapped[list["TeamMembershipEntity"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    project_administrator_links: Mapped[list["ProjectAdministratorEntity"]] = relationship(
        foreign_keys="ProjectAdministratorEntity.user_id",
        back_populates="user",
        cascade="all, delete-orphan",
    )


class TeamEntity(Base):
    """One Scrum team that owns one or more Jira projects in this company."""

    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    member_links: Mapped[list["TeamMembershipEntity"]] = relationship(
        back_populates="team",
        cascade="all, delete-orphan",
    )
    projects: Mapped[list[ProjectEntity]] = relationship(back_populates="owning_team")


class TeamMembershipEntity(Base):
    """An active user's membership in one Scrum team."""

    __tablename__ = "team_memberships"
    __table_args__ = (UniqueConstraint("user_id", "team_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id", ondelete="CASCADE"), index=True)
    scrum_role: Mapped[str | None] = mapped_column(String(50))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    user: Mapped[UserEntity] = relationship(back_populates="team_links")
    team: Mapped[TeamEntity] = relationship(back_populates="member_links")


class ProjectAdministratorEntity(Base):
    """A user allowed to administer one project without company-wide admin rights."""

    __tablename__ = "project_administrators"
    __table_args__ = (UniqueConstraint("user_id", "project_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    granted_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    user: Mapped[UserEntity] = relationship(
        foreign_keys=[user_id],
        back_populates="project_administrator_links",
    )
    project: Mapped[ProjectEntity] = relationship(back_populates="administrator_links")
    granted_by: Mapped[UserEntity | None] = relationship(foreign_keys=[granted_by_user_id])
