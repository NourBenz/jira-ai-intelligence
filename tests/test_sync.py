from contextlib import suppress
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import (
    Base,
    ChangelogEntity,
    CommentEntity,
    IssueEntity,
    ProjectEntity,
    SprintEntity,
    SyncChangeEntity,
    SyncRunEntity,
)
from app.database.session import create_database_engine
from app.models.ticket import Ticket
from app.services.sync_observability_service import SyncObservabilityService
from app.services.sync_service import SyncService


class FakeJiraService:
    incremental_watermark = None

    def get_projects(self):
        return [{"id": "10000", "key": "T1", "name": "T1"}]

    def get_project_issues(self, project_key):
        return [Ticket(id="10001", key="T1-1", summary="Stored issue", labels=[])]

    def get_issue_changelog(self, issue_key):
        return [
            {
                "id": "90001",
                "created": "2026-07-12T10:00:00Z",
                "author": {"displayName": "Alice"},
                "items": [{"field": "status", "toString": "To Do"}],
            }
        ]

    def get_comments(self, issue_key):
        return [
            {
                "id": "70001",
                "issue_key": issue_key,
                "author": "Alice",
                "body": "The OAuth token expired.",
                "created": "2026-07-12T11:00:00Z",
                "updated": "2026-07-12T11:05:00Z",
            }
        ]

    def get_updated_project_issues(self, project_key, updated_since):
        self.incremental_watermark = updated_since
        return [
            Ticket(
                id="10001",
                key="T1-1",
                summary="Updated stored issue",
                labels=["updated"],
            )
        ]

    def get_boards(self):
        return {"values": [{"id": 34, "location": {"projectKey": "T1"}}]}

    def get_sprints(self, board_id):
        return {
            "values": [
                {
                    "id": 69,
                    "name": "T1 Sprint 3",
                    "state": "active",
                    "originBoardId": board_id,
                }
            ]
        }

    def get_sprint_issues(self, sprint_id):
        return [Ticket(id="10001", key="T1-1", summary="Stored issue")]


def _session():
    engine = create_database_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def test_full_sync_is_idempotent_and_records_counts():
    with _session() as session:
        service = SyncService(session, FakeJiraService())
        first = service.full_sync("T1")
        second = service.full_sync("T1")

        assert first.status == "completed"
        assert first.issues_processed == 1
        assert first.sprints_processed == 1
        assert first.changelogs_processed == 1
        assert first.comments_processed == 1
        assert second.status == "completed"
        assert session.scalar(select(func.count()).select_from(ProjectEntity)) == 1
        assert session.scalar(select(func.count()).select_from(IssueEntity)) == 1
        assert session.scalar(select(func.count()).select_from(SprintEntity)) == 1
        assert session.scalar(select(func.count()).select_from(ChangelogEntity)) == 1
        assert session.scalar(select(func.count()).select_from(CommentEntity)) == 1
        assert session.scalar(select(func.count()).select_from(SyncRunEntity)) == 2
        changes = list(session.scalars(select(SyncChangeEntity).order_by(SyncChangeEntity.id)))
        assert [change.change_type for change in changes] == ["created", "unchanged"]
        assert changes[0].issue_key == "T1-1"
        assert changes[0].comments_inspected == 1


def test_failed_sync_records_sanitized_failure():
    class BrokenJiraService(FakeJiraService):
        def get_project_issues(self, project_key):
            raise RuntimeError("secret upstream detail")

    with _session() as session:
        service = SyncService(session, BrokenJiraService())
        with suppress(RuntimeError):
            service.full_sync("T1")

        run = session.scalar(select(SyncRunEntity))
        assert run.status == "failed"
        assert run.error_message == "Jira synchronization failed."
        assert "secret" not in run.error_message
        assert session.scalar(select(func.count()).select_from(ProjectEntity)) == 0


def test_incremental_sync_uses_watermark_and_updates_existing_issue():
    with _session() as session:
        jira = FakeJiraService()
        service = SyncService(session, jira)
        service.full_sync("T1")

        run = service.incremental_sync("T1")

        assert run.mode == "incremental"
        assert run.status == "completed"
        assert run.issues_processed == 1
        assert jira.incremental_watermark is not None
        assert len(jira.incremental_watermark) == 16
        issue = session.scalar(select(IssueEntity))
        assert issue.summary == "Updated stored issue"
        assert issue.labels == ["updated"]
        assert session.scalar(select(func.count()).select_from(IssueEntity)) == 1
        assert session.scalar(select(func.count()).select_from(ChangelogEntity)) == 1
        assert session.scalar(select(func.count()).select_from(CommentEntity)) == 1
        change = session.scalar(
            select(SyncChangeEntity).where(SyncChangeEntity.sync_run_id == run.id)
        )
        assert change.change_type == "updated"
        assert {"summary", "labels"}.issubset(change.changed_fields)
        assert change.before_values["summary"] == "Stored issue"
        assert change.after_values["summary"] == "Updated stored issue"


def test_incremental_sync_without_baseline_falls_back_to_full():
    with _session() as session:
        run = SyncService(session, FakeJiraService()).incremental_sync("T1")

        assert run.mode == "full"
        assert run.status == "completed"


def test_update_check_detects_newer_jira_issue_and_uses_shared_cache():
    class LatestIssueService:
        calls = 0

        def get_latest_updated_project_issue(self, project_key):
            self.calls += 1
            return Ticket(
                id="10001",
                key="T1-1",
                updated=datetime(2026, 8, 5, 11, 0, tzinfo=UTC),
            )

    with _session() as session:
        project = ProjectEntity(
            jira_id="10000",
            key="T1",
            name="T1",
            jira_checked_at=datetime.now(UTC) - timedelta(minutes=2),
        )
        project.issues.append(
            IssueEntity(
                jira_id="10001",
                key="T1-1",
                labels=[],
                updated_at=datetime(2026, 8, 5, 10, 0, tzinfo=UTC),
            )
        )
        session.add(project)
        session.commit()
        jira = LatestIssueService()
        service = SyncObservabilityService(session, jira)

        first = service.check("T1")
        second = service.check("T1")

        assert first.jira_updates_available is True
        assert first.jira_latest_issue_key == "T1-1"
        assert second.jira_updates_available is True
        assert jira.calls == 1
