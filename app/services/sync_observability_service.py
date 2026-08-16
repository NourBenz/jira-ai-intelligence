"""Cache lightweight Jira freshness checks for shared dashboard notifications."""

from datetime import UTC, datetime, timedelta

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.database.repositories import JiraRepository
from app.models.ticket import Ticket
from app.services.jira_service import JiraService


class SyncObservabilityService:
    """Compare Jira's newest issue timestamp with the synchronized snapshot."""

    cache_duration = timedelta(seconds=60)

    def __init__(self, session: Session, jira_service: JiraService) -> None:
        self.session = session
        self.jira_service = jira_service
        self.repository = JiraRepository(session)

    @staticmethod
    def _utc(value: datetime) -> datetime:
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)

    def check(self, project_key: str, *, force: bool = False):
        project = self.repository.get_project(project_key)
        if project is None:
            raise HTTPException(status_code=404, detail="Project is not available.")
        now = datetime.now(UTC)
        if (
            not force
            and project.jira_checked_at is not None
            and now - self._utc(project.jira_checked_at) < self.cache_duration
        ):
            return project

        try:
            latest = self.jira_service.get_latest_updated_project_issue(project_key)
            self._apply_latest(project, latest)
            project.jira_update_check_error = None
        except HTTPException:
            project.jira_update_check_error = "Jira update check is temporarily unavailable."
        project.jira_checked_at = now
        self.session.commit()
        self.session.refresh(project)
        return project

    def _apply_latest(self, project, latest: Ticket | None) -> None:
        if latest is None or latest.updated is None:
            project.jira_latest_issue_key = None
            project.jira_latest_updated_at = None
            project.jira_updates_available = False
            return
        stored = self.repository.get_issue_by_key(latest.key)
        project.jira_latest_issue_key = latest.key
        project.jira_latest_updated_at = latest.updated
        project.jira_updates_available = (
            stored is None
            or stored.updated_at is None
            or self._utc(stored.updated_at) < self._utc(latest.updated)
        )
