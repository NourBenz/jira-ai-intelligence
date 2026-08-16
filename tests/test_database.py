from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import Base, IssueEntity, ProjectEntity, SyncRunEntity
from app.database.session import create_database_engine


def test_database_schema_stores_project_issue_and_sync_run():
    engine = create_database_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        project = ProjectEntity(jira_id="10000", key="T1", name="T1")
        project.issues.append(
            IssueEntity(
                jira_id="10001",
                key="T1-1",
                summary="Persist Jira issue",
                labels=["backend"],
            )
        )
        session.add(project)
        session.add(
            SyncRunEntity(
                project_key="T1",
                mode="full",
                status="completed",
                started_at=datetime.now(UTC),
                projects_processed=1,
                issues_processed=1,
                sprints_processed=0,
                changelogs_processed=0,
            )
        )
        session.commit()

        stored = session.scalar(select(IssueEntity).where(IssueEntity.key == "T1-1"))
        assert stored is not None
        assert stored.project.key == "T1"
        assert stored.labels == ["backend"]


def test_database_metadata_contains_persistence_and_access_tables():
    assert set(Base.metadata.tables) == {
        "projects",
        "issues",
        "sprints",
        "sprint_issues",
        "changelogs",
        "comments",
        "sync_runs",
        "rag_chunks",
        "users",
        "teams",
        "team_memberships",
        "project_administrators",
        "sync_changes",
    }


def test_user_profile_fields_are_optional_and_email_is_unique():
    users = Base.metadata.tables["users"]

    assert users.c.first_name.nullable
    assert users.c.last_name.nullable
    assert users.c.email.nullable
    assert users.c.email.unique or any(
        index.unique and "email" in {column.name for column in index.columns}
        for index in users.indexes
    )
