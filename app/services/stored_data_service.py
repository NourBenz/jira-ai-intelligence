from sqlalchemy.orm import Session

from app.database.entities import IssueEntity
from app.database.repositories import JiraRepository
from app.models.ticket import Ticket
from app.services.analytics_service import AnalyticsService
from app.services.risk_service import RiskService


class StoredDataService:
    """Read synchronized Jira data without contacting Jira Cloud."""

    def __init__(self, session: Session) -> None:
        self.repository = JiraRepository(session)

    def get_project_issues(self, project_key: str) -> list[Ticket]:
        return [self._ticket(entity) for entity in self.repository.list_project_issues(project_key)]

    def get_project_issue(self, project_key: str, issue_key: str) -> Ticket | None:
        """Read one synchronized issue through a project-scoped exact lookup."""
        entity = self.repository.get_project_issue(project_key, issue_key)
        return self._ticket(entity) if entity is not None else None

    def get_project_comments(self, project_key: str) -> dict[str, list[dict]]:
        return self.repository.project_comments(project_key)

    def get_project_overview(self, project_key: str):
        issues = self.get_project_issues(project_key)
        return AnalyticsService.project_overview(project_key, issues) if issues else None

    def get_project_activity(self, project_key: str, stale_days: int, limit: int):
        issues = self.get_project_issues(project_key)
        return (
            AnalyticsService.project_activity(project_key, issues, stale_days, limit)
            if issues
            else None
        )

    def get_project_insights(self, project_key: str, weeks: int):
        issues = self.get_project_issues(project_key)
        return AnalyticsService.project_insights(project_key, issues, weeks) if issues else None

    def get_project_history(self, project_key: str, weeks: int):
        issues = self.get_project_issues(project_key)
        if not issues:
            return None
        return AnalyticsService.history_metrics(
            project_key,
            issues,
            self.repository.project_histories(project_key),
            weeks,
        )

    def get_project_risks(self, project_key: str):
        """Return the canonical deterministic risk analysis for synchronized data."""
        issues = self.get_project_issues(project_key)
        if not issues:
            return None
        overview = AnalyticsService.project_overview(project_key, issues)
        activity = AnalyticsService.project_activity(project_key, issues, 14, 20)
        insights = AnalyticsService.project_insights(project_key, issues, 8)
        return RiskService.analyze(project_key, issues, overview, activity, insights)

    def get_project_sprint_summary(self, project_key: str):
        """Build authoritative sprint membership metrics from synchronized data."""
        sprints = self.repository.list_project_sprints(project_key)
        if not sprints:
            return None
        summaries = []
        for sprint in sprints:
            issues = [
                self._ticket(entity)
                for entity in self.repository.list_sprint_issues(sprint.jira_id)
            ]
            completion = AnalyticsService.sprint_completion(sprint.jira_id, issues)
            summaries.append(
                {
                    "sprint_id": sprint.jira_id,
                    "board_id": sprint.board_id or 0,
                    "name": sprint.name,
                    "state": sprint.state,
                    "start_date": sprint.start_date.isoformat() if sprint.start_date else None,
                    "end_date": sprint.end_date.isoformat() if sprint.end_date else None,
                    "issue_count": completion["total"],
                    "completed_count": completion["done"],
                    "open_count": completion["remaining"],
                    "completion_rate": completion["completion_rate"],
                }
            )
        return {
            "project_key": project_key,
            "total_sprints": len(summaries),
            "sprints": summaries,
        }

    def get_sprint_issues(self, sprint_id: int) -> list[Ticket] | None:
        """Return a sprint snapshot, distinguishing an empty sprint from an unknown one."""
        if self.repository.get_sprint_by_jira_id(sprint_id) is None:
            return None
        return [self._ticket(entity) for entity in self.repository.list_sprint_issues(sprint_id)]

    def get_sprint_performance(self, sprint_id: int):
        sprint = self.repository.get_sprint_by_jira_id(sprint_id)
        if sprint is None:
            return None
        entities = self.repository.list_sprint_issues(sprint_id)
        issues = [self._ticket(entity) for entity in entities]
        if not issues:
            return None
        project_key = sprint.project.key if sprint.project else ""
        return AnalyticsService.sprint_performance(
            {
                "id": sprint.jira_id,
                "name": sprint.name,
                "startDate": (sprint.start_date.isoformat() if sprint.start_date else None),
            },
            issues,
            self.repository.project_histories(project_key),
        )

    @staticmethod
    def _ticket(entity: IssueEntity) -> Ticket:
        return Ticket(
            id=entity.jira_id,
            key=entity.key,
            summary=entity.summary,
            description=entity.description,
            status=entity.status,
            status_category=entity.status_category,
            priority=entity.priority,
            issue_type=entity.issue_type,
            assignee=entity.assignee,
            reporter=entity.reporter,
            created=entity.created_at,
            updated=entity.updated_at,
            resolution_date=entity.resolution_date,
            due_date=entity.due_date,
            story_points=entity.story_points,
            labels=entity.labels or [],
        )
