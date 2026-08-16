"""Build bounded, project-scoped evidence packages from synchronized Jira data."""

from app.services.analytics_service import AnalyticsService
from app.services.risk_service import RiskService
from app.services.stored_data_service import StoredDataService


class EvidenceService:
    """Prepare stored facts for deterministic and model-assisted intelligence."""

    def __init__(self, stored_data: StoredDataService) -> None:
        self.stored_data = stored_data

    def build_project_sprint_summary(self, project_key: str):
        """Return synchronized sprint facts for deterministic question routing."""
        return self.stored_data.get_project_sprint_summary(project_key)

    def build_project_evidence(self, project_key: str) -> dict | None:
        issues = self.stored_data.get_project_issues(project_key)
        if not issues:
            return None
        overview = self.stored_data.get_project_overview(project_key)
        activity = self.stored_data.get_project_activity(project_key, 14, 10)
        insights = self.stored_data.get_project_insights(project_key, 8)
        history = self.stored_data.get_project_history(project_key, 8)
        if overview is None or activity is None or insights is None:
            return None

        completed_issue_keys = [
            issue.key for issue in issues if AnalyticsService.is_completed(issue)
        ]
        open_issue_keys = [
            issue.key for issue in issues if not AnalyticsService.is_completed(issue)
        ]
        risk_analysis = RiskService.analyze(project_key, issues, overview, activity, insights)

        return {
            "project_key": project_key,
            "overview": overview,
            "activity": {
                "average_issue_age_days": activity["average_issue_age_days"],
                "stale_issue_keys": [issue.key for issue in activity["stale_issues"]],
            },
            "insights": {
                "workload_by_assignee_status": insights["workload_by_assignee_status"],
                "overdue_by_assignee": insights["overdue_by_assignee"],
                "blocked_issue_keys": [issue.key for issue in insights["blocked_issues"]],
            },
            "history": history,
            "risk_signals": risk_analysis["signals"],
            "issue_state_context": {
                "completed_issue_keys": completed_issue_keys,
                "open_issue_keys": open_issue_keys,
                "interpretation": (
                    "Completed issues are delivery progress and are not risks by themselves."
                ),
            },
            "issues": [
                {
                    "key": issue.key,
                    "summary": issue.summary,
                    "status": issue.status,
                    "status_category": issue.status_category,
                    "priority": issue.priority,
                    "assignee": issue.assignee,
                }
                for issue in issues[:50]
            ],
            "known_limitations": risk_analysis["limitations"],
        }
