from typing import Any

from app.jira.jira_client import JiraClient
from app.models.ticket import Ticket
from app.schemas.search import IssueSearchQuery
from app.services.analytics_service import AnalyticsService


class JiraService:
    def __init__(self) -> None:
        self.client = JiraClient()

    def get_projects(self) -> list[dict[str, Any]]:
        return self.client.get_projects()

    def get_boards(self) -> dict[str, Any]:
        return self.client.get_boards()

    def get_sprints(self, board_id: int) -> dict[str, Any]:
        return self.client.get_sprints(board_id)

    def get_users(self) -> list[Any]:
        return self.client.get_users()

    def get_project_issues(
        self,
        project_key: str,
    ) -> list[Ticket]:
        raw_issues = self.client.get_issues(project_key)

        return [Ticket(**issue) for issue in raw_issues]

    def get_updated_project_issues(
        self,
        project_key: str,
        updated_since: str,
    ) -> list[Ticket]:
        return [
            Ticket(**issue) for issue in self.client.get_updated_issues(project_key, updated_since)
        ]

    def get_latest_updated_project_issue(self, project_key: str) -> Ticket | None:
        issue = self.client.get_latest_updated_issue(project_key)
        return Ticket(**issue) if issue is not None else None

    def search_project_issues(
        self,
        project_key: str,
        query: IssueSearchQuery,
    ) -> dict[str, object]:
        result = self.client.search_issues(
            project_key,
            status=query.status,
            assignee=query.assignee,
            priority=query.priority,
            issue_type=query.issue_type,
            label=query.label,
            created_from=(query.created_from.isoformat() if query.created_from else None),
            created_to=(query.created_to.isoformat() if query.created_to else None),
            sort_by=query.sort_by,
            order=query.order,
            limit=query.limit,
            page_token=query.page_token,
        )
        issues = [Ticket(**issue) for issue in result["issues"]]
        return {
            "project_key": project_key,
            "issues": issues,
            "returned": len(issues),
            "is_last": result["is_last"],
            "next_page_token": result["next_page_token"],
        }

    def get_issue(
        self,
        issue_key: str,
    ) -> Ticket:
        raw_issue = self.client.get_issue(issue_key)

        return Ticket(**raw_issue)

    def get_comments(
        self,
        issue_key: str,
    ) -> list[dict[str, Any]]:
        return self.client.get_comments(issue_key)

    def get_issue_changelog(self, issue_key: str) -> list[dict[str, Any]]:
        return self.client.get_issue_changelog(issue_key)

    def get_sprint_issues(
        self,
        sprint_id: int,
    ) -> list[Ticket]:
        raw_issues = self.client.get_sprint_issues(sprint_id)

        return [Ticket(**issue) for issue in raw_issues]

    def get_issue_status_counts(
        self,
        project_key: str,
    ) -> dict[str, int]:
        return AnalyticsService.status_counts(self.get_project_issues(project_key))

    def get_workload_by_assignee(
        self,
        project_key: str,
    ) -> dict[str, int]:
        return AnalyticsService.workload(self.get_project_issues(project_key))

    def get_issue_priority_counts(
        self,
        project_key: str,
    ) -> dict[str, int]:
        return AnalyticsService.priority_counts(self.get_project_issues(project_key))

    def get_issue_type_counts(
        self,
        project_key: str,
    ) -> dict[str, int]:
        return AnalyticsService.type_counts(self.get_project_issues(project_key))

    def get_sprint_completion(
        self,
        sprint_id: int,
    ) -> dict[str, int | float]:
        return AnalyticsService.sprint_completion(
            sprint_id,
            self.get_sprint_issues(sprint_id),
        )

    def get_project_sprint_summary(
        self,
        project_key: str,
    ) -> dict[str, object] | None:
        """Return deterministic sprint names, states, and issue counts."""
        summaries = []
        seen_sprint_ids: set[int] = set()
        for board in self.get_boards().get("values", []):
            location = board.get("location") or {}
            board_project = str(location.get("projectKey") or "")
            if board_project.casefold() != project_key.casefold():
                continue
            board_id = int(board["id"])
            for sprint in self.get_sprints(board_id).get("values", []):
                sprint_id = int(sprint["id"])
                if sprint_id in seen_sprint_ids:
                    continue
                seen_sprint_ids.add(sprint_id)
                issues = self.get_sprint_issues(sprint_id)
                completion = AnalyticsService.sprint_completion(
                    sprint_id,
                    issues,
                )
                summaries.append(
                    {
                        "sprint_id": sprint_id,
                        "board_id": board_id,
                        "name": str(sprint.get("name") or sprint_id),
                        "state": str(sprint.get("state") or "unknown"),
                        "start_date": sprint.get("startDate"),
                        "end_date": sprint.get("endDate"),
                        "issue_count": completion["total"],
                        "completed_count": completion["done"],
                        "open_count": completion["remaining"],
                        "completion_rate": completion["completion_rate"],
                    }
                )
        if not summaries:
            return None
        return {
            "project_key": project_key,
            "total_sprints": len(summaries),
            "sprints": summaries,
        }

    def get_overdue_issues(
        self,
        project_key: str,
    ) -> list[Ticket]:
        return AnalyticsService.overdue_issues(self.get_project_issues(project_key))

    @staticmethod
    def _filter_overdue_issues(
        issues: list[Ticket],
    ) -> list[Ticket]:
        """Apply overdue rules to an already-fetched issue collection."""

        return AnalyticsService.overdue_issues(issues)

    def get_overdue_summary(
        self,
        project_key: str,
    ) -> dict[str, int | list[Ticket]] | None:
        """Return overdue analytics after fetching project issues once.

        ``None`` distinguishes a project with no returned issues from a
        project that has issues but no overdue work.
        """
        issues = self.get_project_issues(project_key)

        if not issues:
            return None

        overdue_issues = self._filter_overdue_issues(issues)

        return {
            "total": len(overdue_issues),
            "issues": overdue_issues,
        }

    def get_project_overview(
        self,
        project_key: str,
    ) -> dict[str, object] | None:
        """Build all overview metrics from one Jira issue fetch."""
        issues = self.get_project_issues(project_key)
        if not issues:
            return None
        return AnalyticsService.project_overview(project_key, issues)

    def get_project_activity(
        self,
        project_key: str,
        stale_days: int,
        limit: int,
    ) -> dict[str, object] | None:
        issues = self.get_project_issues(project_key)
        if not issues:
            return None
        return AnalyticsService.project_activity(
            project_key,
            issues,
            stale_days,
            limit,
        )

    def get_project_insights(
        self,
        project_key: str,
        weeks: int,
    ) -> dict[str, object] | None:
        """Build extended analytics from one Jira issue fetch."""
        issues = self.get_project_issues(project_key)
        if not issues:
            return None
        return AnalyticsService.project_insights(
            project_key,
            issues,
            weeks,
        )

    def get_project_history_metrics(
        self,
        project_key: str,
        weeks: int,
    ) -> dict[str, object] | None:
        issues = self.get_project_issues(project_key)
        if not issues:
            return None
        histories = {issue.key: self.client.get_issue_changelog(issue.key) for issue in issues}
        return AnalyticsService.history_metrics(project_key, issues, histories, weeks)

    def get_sprint_performance(
        self,
        sprint_id: int,
    ) -> dict[str, object] | None:
        issues = self.get_sprint_issues(sprint_id)
        if not issues:
            return None
        sprint = self.client.get_sprint(sprint_id)
        candidates = issues
        board_id = sprint.get("originBoardId")
        if isinstance(board_id, int):
            board = self.client.get_board(board_id)
            location = board.get("location") or {}
            project_key = location.get("projectKey")
            if isinstance(project_key, str) and project_key:
                candidates = self.get_project_issues(project_key)
        histories = {issue.key: self.client.get_issue_changelog(issue.key) for issue in candidates}
        return AnalyticsService.sprint_performance(sprint, issues, histories)
