from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.database.entities import IssueEntity, ProjectEntity, SyncRunEntity
from app.database.repositories import JiraRepository
from app.models.ticket import Ticket
from app.services.jira_service import JiraService


class SyncService:
    def __init__(self, session: Session, jira_service: JiraService) -> None:
        self.session, self.jira_service = session, jira_service
        self.repository = JiraRepository(session)

    def _require_run(self, run_id: int) -> SyncRunEntity:
        """Return a just-created sync run, enforcing the repository invariant."""
        run = self.repository.get_sync_run(run_id)
        if run is None:
            raise RuntimeError("The synchronization run could not be reloaded.")
        return run

    @staticmethod
    def _json_value(value):
        if hasattr(value, "isoformat"):
            return value.isoformat()
        return value

    @classmethod
    def _entity_snapshot(cls, issue: IssueEntity | None) -> dict:
        if issue is None:
            return {}
        return {
            "summary": issue.summary,
            "description": issue.description,
            "status": issue.status,
            "status_category": issue.status_category,
            "priority": issue.priority,
            "issue_type": issue.issue_type,
            "assignee": issue.assignee,
            "reporter": issue.reporter,
            "created": cls._json_value(issue.created_at),
            "updated": cls._json_value(issue.updated_at),
            "resolution_date": cls._json_value(issue.resolution_date),
            "due_date": cls._json_value(issue.due_date),
            "story_points": issue.story_points,
            "labels": issue.labels or [],
        }

    @classmethod
    def _ticket_snapshot(cls, issue: Ticket) -> dict:
        return {
            "summary": issue.summary,
            "description": issue.description,
            "status": issue.status,
            "status_category": issue.status_category,
            "priority": issue.priority,
            "issue_type": issue.issue_type,
            "assignee": issue.assignee,
            "reporter": issue.reporter,
            "created": cls._json_value(issue.created),
            "updated": cls._json_value(issue.updated),
            "resolution_date": cls._json_value(issue.resolution_date),
            "due_date": cls._json_value(issue.due_date),
            "story_points": issue.story_points,
            "labels": issue.labels,
        }

    def _process_issue(
        self,
        run: SyncRunEntity,
        project: ProjectEntity,
        ticket: Ticket,
    ) -> tuple[int, int]:
        existing = self.repository.get_issue_by_jira_id(ticket.id)
        before = self._entity_snapshot(existing)
        after = self._ticket_snapshot(ticket)
        changed_fields = [key for key, value in after.items() if before.get(key) != value]
        change_type = (
            "created" if existing is None else "updated" if changed_fields else "unchanged"
        )
        issue = self.repository.upsert_issue(project, ticket)
        histories = self.jira_service.get_issue_changelog(ticket.key)
        for history in histories:
            self.repository.upsert_changelog(issue, history)
        comments = self.jira_service.get_comments(ticket.key)
        comments_inspected = self.repository.replace_comments(issue, comments)
        self.repository.record_sync_change(
            run,
            issue_key=ticket.key,
            change_type=change_type,
            changed_fields=changed_fields,
            before_values={key: before.get(key) for key in changed_fields if key in before},
            after_values={key: after.get(key) for key in changed_fields},
            changelogs_inspected=len(histories),
            comments_inspected=comments_inspected,
        )
        return len(histories), comments_inspected

    @staticmethod
    def _mark_project_synchronized(project: ProjectEntity, issues: list[Ticket]) -> None:
        now = datetime.now(UTC)
        project.synchronized_at = now
        project.jira_checked_at = now
        project.jira_updates_available = False
        project.jira_update_check_error = None
        latest = max(
            (issue for issue in issues if issue.updated is not None),
            key=lambda issue: issue.updated or datetime.min.replace(tzinfo=UTC),
            default=None,
        )
        if latest is not None:
            project.jira_latest_issue_key = latest.key
            project.jira_latest_updated_at = latest.updated

    def _sync_sprint_memberships(
        self,
        project_key: str,
        project: ProjectEntity,
    ) -> int:
        """Refresh sprint membership identically for full and incremental syncs."""
        sprint_count = 0
        for board in self.jira_service.get_boards().get("values", []):
            if (board.get("location") or {}).get("projectKey") != project_key:
                continue
            for sprint in self.jira_service.get_sprints(int(board["id"])).get("values", []):
                sprint_entity = self.repository.upsert_sprint(project, sprint)
                sprint_issues = self.jira_service.get_sprint_issues(int(sprint["id"]))
                self.repository.replace_sprint_issues(sprint_entity, sprint_issues)
                sprint_count += 1
        return sprint_count

    def full_sync(self, project_key: str):
        run = self.repository.create_sync_run(project_key)
        self.session.commit()
        run_id = run.id
        try:
            project_data = next(
                (p for p in self.jira_service.get_projects() if p["key"] == project_key), None
            )
            if project_data is None:
                raise HTTPException(
                    status_code=404, detail=f"Project '{project_key}' was not found in Jira."
                )
            project = self.repository.upsert_project(project_data)
            issues = self.jira_service.get_project_issues(project_key)
            changelog_count = 0
            comment_count = 0
            for ticket in issues:
                histories, comments = self._process_issue(run, project, ticket)
                changelog_count += histories
                comment_count += comments
            sprint_count = self._sync_sprint_memberships(project_key, project)
            run = self._require_run(run_id)
            run.status, run.completed_at = "completed", datetime.now(UTC)
            run.projects_processed, run.issues_processed = 1, len(issues)
            run.sprints_processed, run.changelogs_processed = sprint_count, changelog_count
            run.comments_processed = comment_count
            self._mark_project_synchronized(project, issues)
            self.session.commit()
            self.session.refresh(run)
            return run
        except Exception:
            self.session.rollback()
            run = self._require_run(run_id)
            run.status, run.completed_at = "failed", datetime.now(UTC)
            run.error_message = "Jira synchronization failed."
            self.session.commit()
            raise

    def incremental_sync(self, project_key: str):
        previous = self.repository.last_successful_sync(project_key)
        project = self.repository.get_project(project_key)
        if previous is None or previous.completed_at is None or project is None:
            return self.full_sync(project_key)

        run = self.repository.create_sync_run(project_key, mode="incremental")
        self.session.commit()
        run_id = run.id
        watermark = previous.completed_at.strftime("%Y-%m-%d %H:%M")
        try:
            issues = self.jira_service.get_updated_project_issues(project_key, watermark)
            changelog_count = 0
            comment_count = 0
            for ticket in issues:
                histories, comments = self._process_issue(run, project, ticket)
                changelog_count += histories
                comment_count += comments

            sprint_count = self._sync_sprint_memberships(project_key, project)

            run = self._require_run(run_id)
            run.status, run.completed_at = "completed", datetime.now(UTC)
            run.projects_processed = 1
            run.issues_processed = len(issues)
            run.sprints_processed = sprint_count
            run.changelogs_processed = changelog_count
            run.comments_processed = comment_count
            self._mark_project_synchronized(project, issues)
            self.session.commit()
            self.session.refresh(run)
            return run
        except Exception:
            self.session.rollback()
            run = self._require_run(run_id)
            run.status, run.completed_at = "failed", datetime.now(UTC)
            run.error_message = "Incremental Jira synchronization failed."
            self.session.commit()
            raise
