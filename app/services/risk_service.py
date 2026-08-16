"""Central deterministic delivery-risk rules shared by APIs and the UI."""

from typing import Any

from app.models.ticket import Ticket
from app.services.analytics_service import AnalyticsService


class RiskService:
    """Evaluate synchronized Jira facts with one documented set of thresholds."""

    @classmethod
    def analyze(
        cls,
        project_key: str,
        issues: list[Ticket],
        overview: dict[str, Any],
        activity: dict[str, Any],
        insights: dict[str, Any],
    ) -> dict[str, Any]:
        open_issues = [issue for issue in issues if not AnalyticsService.is_completed(issue)]
        overdue_issues = AnalyticsService.overdue_issues(open_issues)
        stale_issues = activity["stale_issues"]
        blocked_issues = insights["blocked_issues"]
        unassigned_issues = [issue for issue in open_issues if issue.assignee is None]
        signals: list[dict[str, Any]] = []

        if blocked_issues:
            keys = [issue.key for issue in blocked_issues[:5]]
            signals.append(
                cls._signal(
                    "blocked_work",
                    "Blocked work",
                    "high",
                    f"{len(blocked_issues)} open issue(s) are blocked.",
                    keys,
                    "Review blocked issues "
                    f"{', '.join(keys)}, identify each blocker owner, and agree on the "
                    "next unblock action.",
                )
            )
        if overdue_issues:
            keys = [issue.key for issue in overdue_issues[:5]]
            signals.append(
                cls._signal(
                    "overdue_work",
                    "Overdue work",
                    "high",
                    f"{len(overdue_issues)} open issue(s) are overdue.",
                    keys,
                    "Review overdue issues "
                    f"{', '.join(keys)} with their owners and either complete, replan, "
                    "or reprioritize them.",
                )
            )
        if stale_issues:
            keys = [issue.key for issue in stale_issues[:5]]
            signals.append(
                cls._signal(
                    "stale_work",
                    "Stale work",
                    "medium",
                    f"{len(stale_issues)} open issue(s) have not been updated within 14 days.",
                    keys,
                    "Review stale issues "
                    f"{', '.join(keys)} with their owners and record a clear next step "
                    "for each one.",
                )
            )
        if unassigned_issues:
            keys = [issue.key for issue in unassigned_issues[:5]]
            signals.append(
                cls._signal(
                    "unassigned_work",
                    "Unassigned work",
                    "medium",
                    f"{len(unassigned_issues)} open issue(s) are unassigned.",
                    keys,
                    f"Assign an accountable owner to unassigned issues {', '.join(keys)}.",
                )
            )

        assigned_open = [issue for issue in open_issues if issue.assignee]
        assignee_counts: dict[str, int] = {}
        for issue in assigned_open:
            if issue.assignee is not None:
                assignee_counts[issue.assignee] = assignee_counts.get(issue.assignee, 0) + 1
        if assignee_counts:
            busiest_assignee, busiest_count = max(assignee_counts.items(), key=lambda item: item[1])
            share = busiest_count / len(assigned_open)
            if share > 0.5 and busiest_count >= 3:
                signals.append(
                    cls._signal(
                        "workload_concentration",
                        "Workload concentration",
                        "medium",
                        f"{busiest_assignee} owns {busiest_count} of "
                        f"{len(assigned_open)} assigned open issues ({share:.0%}).",
                        [],
                        f"Review {busiest_assignee}'s open workload and redistribute work "
                        "where another team member has capacity.",
                    )
                )

        if overview["open_count"] >= 5 and overview["completion_rate"] < 25:
            signals.append(
                cls._signal(
                    "low_completion",
                    "Low completion rate",
                    "medium",
                    f"{overview['open_count']} of {overview['total_issues']} issues remain "
                    f"open; completion is {overview['completion_rate']}%.",
                    [],
                    "Review the open backlog and agree on the highest-priority issues "
                    "to finish next.",
                )
            )

        return {
            "project_key": project_key,
            "signals": signals,
            "limitations": cls.limitations(issues),
        }

    @staticmethod
    def limitations(issues: list[Ticket]) -> list[str]:
        """Report missing Jira fields without converting absence into a risk."""
        limitations = []
        if not any(issue.due_date for issue in issues):
            limitations.append("No issue due dates are available.")
        if not any(issue.story_points is not None for issue in issues):
            limitations.append("No story-point estimates are available.")
        if not any(issue.labels for issue in issues):
            limitations.append("No issue labels are available.")
        return limitations

    @staticmethod
    def _signal(
        signal_type: str,
        label: str,
        severity: str,
        fact: str,
        issue_keys: list[str],
        recommended_action: str,
    ) -> dict[str, Any]:
        return {
            "type": signal_type,
            "label": label,
            "severity": severity,
            "fact": fact,
            "issue_keys": issue_keys,
            "recommended_action": recommended_action,
        }
