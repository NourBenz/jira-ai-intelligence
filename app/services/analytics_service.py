"""Deterministic analytics over already-fetched Jira tickets."""

from collections.abc import Callable, Iterable
from datetime import UTC, date, datetime, timedelta
from typing import cast

from app.models.ticket import Ticket


class AnalyticsService:
    """Pure calculations that never call Jira."""

    _fallback_done_statuses = {"done", "closed", "resolved"}
    _not_started_statuses = {"to do", "todo", "open", "backlog", "new"}

    @classmethod
    def is_completed(cls, issue: Ticket) -> bool:
        if issue.status_category:
            return issue.status_category.casefold() == "done"
        return bool(issue.status and issue.status.casefold() in cls._fallback_done_statuses)

    @staticmethod
    def status_counts(issues: list[Ticket]) -> dict[str, int]:
        return AnalyticsService._counts(issue.status or "Unknown" for issue in issues)

    @staticmethod
    def workload(issues: list[Ticket]) -> dict[str, int]:
        return AnalyticsService._counts(issue.assignee or "Unassigned" for issue in issues)

    @staticmethod
    def priority_counts(issues: list[Ticket]) -> dict[str, int]:
        return AnalyticsService._counts(issue.priority or "None" for issue in issues)

    @staticmethod
    def type_counts(issues: list[Ticket]) -> dict[str, int]:
        return AnalyticsService._counts(issue.issue_type or "Unknown" for issue in issues)

    @classmethod
    def sprint_completion(
        cls,
        sprint_id: int,
        issues: list[Ticket],
    ) -> dict[str, int | float]:
        total = len(issues)
        done = sum(cls.is_completed(issue) for issue in issues)
        return {
            "sprint_id": sprint_id,
            "total": total,
            "done": done,
            "remaining": total - done,
            "completion_rate": (round((done / total) * 100, 2) if total else 0.0),
        }

    @classmethod
    def overdue_issues(
        cls,
        issues: list[Ticket],
        today: date | None = None,
    ) -> list[Ticket]:
        comparison_date = today or date.today()
        return [
            issue
            for issue in issues
            if issue.due_date is not None
            and issue.due_date < comparison_date
            and not cls.is_completed(issue)
        ]

    @classmethod
    def project_overview(
        cls,
        project_key: str,
        issues: list[Ticket],
    ) -> dict[str, object]:
        total = len(issues)
        completed = sum(cls.is_completed(issue) for issue in issues)
        overdue = cls.overdue_issues(issues)
        return {
            "project_key": project_key,
            "total_issues": total,
            "status_counts": cls.status_counts(issues),
            "priority_counts": cls.priority_counts(issues),
            "issue_type_counts": cls.type_counts(issues),
            "workload_by_assignee": cls.workload(issues),
            "overdue_count": len(overdue),
            "unassigned_count": sum(
                issue.assignee is None and not cls.is_completed(issue) for issue in issues
            ),
            "completed_count": completed,
            "open_count": total - completed,
            "completion_rate": (round((completed / total) * 100, 2) if total else 0.0),
        }

    @classmethod
    def project_activity(
        cls,
        project_key: str,
        issues: list[Ticket],
        stale_days: int,
        limit: int,
        now: datetime | None = None,
    ) -> dict[str, object]:
        reference = now or datetime.now(UTC)
        created_issues = [issue for issue in issues if issue.created]
        ages = [
            max((reference - cls._as_utc(issue.created)).total_seconds(), 0) / 86400
            for issue in created_issues
            if issue.created is not None
        ]
        open_issues = [issue for issue in issues if not cls.is_completed(issue)]
        oldest = sorted(
            (issue for issue in open_issues if issue.created),
            key=lambda issue: cls._as_utc(cast(datetime, issue.created)),
        )[:limit]
        recent = sorted(
            (issue for issue in issues if issue.updated),
            key=lambda issue: cls._as_utc(cast(datetime, issue.updated)),
            reverse=True,
        )[:limit]
        stale_before = reference - timedelta(days=stale_days)
        stale = sorted(
            (
                issue
                for issue in open_issues
                if issue.updated and cls._as_utc(issue.updated) < stale_before
            ),
            key=lambda issue: cls._as_utc(cast(datetime, issue.updated)),
        )
        return {
            "project_key": project_key,
            "average_issue_age_days": (round(sum(ages) / len(ages), 2) if ages else 0.0),
            "oldest_open_issues": oldest,
            "recently_updated_issues": recent,
            "stale_days": stale_days,
            "stale_issues": stale,
        }

    @classmethod
    def project_insights(
        cls,
        project_key: str,
        issues: list[Ticket],
        weeks: int,
        now: datetime | None = None,
    ) -> dict[str, object]:
        """Build current-state insights without requiring Jira history."""
        reference = cls._as_utc(now or datetime.now(UTC))
        current_week = reference.date() - timedelta(days=reference.weekday())
        week_starts = [current_week - timedelta(weeks=offset) for offset in reversed(range(weeks))]
        created_by_week = {week_start.isoformat(): 0 for week_start in week_starts}
        earliest_week = week_starts[0]
        for issue in issues:
            if issue.created is None:
                continue
            created_date = cls._as_utc(issue.created).date()
            created_week = created_date - timedelta(days=created_date.weekday())
            if earliest_week <= created_week <= current_week:
                created_by_week[created_week.isoformat()] += 1

        labels = cls._counts(label for issue in issues for label in issue.labels)
        workload_by_status = cls._matrix(
            issues,
            lambda issue: issue.assignee or "Unassigned",
            lambda issue: issue.status or "Unknown",
        )
        workload_by_priority = cls._matrix(
            issues,
            lambda issue: issue.assignee or "Unassigned",
            lambda issue: issue.priority or "None",
        )
        overdue = cls.overdue_issues(issues, today=reference.date())
        overdue_by_assignee = cls._counts(issue.assignee or "Unassigned" for issue in overdue)
        overdue_by_priority = cls._counts(issue.priority or "None" for issue in overdue)
        blocked = [
            issue
            for issue in issues
            if not cls.is_completed(issue)
            and (
                bool(issue.status and "block" in issue.status.casefold())
                or any("block" in label.casefold() for label in issue.labels)
            )
        ]
        return {
            "project_key": project_key,
            "weeks": weeks,
            "created_by_week": created_by_week,
            "label_counts": labels,
            "workload_by_assignee_status": workload_by_status,
            "workload_by_assignee_priority": workload_by_priority,
            "overdue_by_assignee": overdue_by_assignee,
            "overdue_by_priority": overdue_by_priority,
            "blocked_count": len(blocked),
            "blocked_issues": blocked,
        }

    @classmethod
    def history_metrics(
        cls,
        project_key: str,
        issues: list[Ticket],
        histories: dict[str, list[dict]],
        weeks: int,
        now: datetime | None = None,
    ) -> dict[str, object]:
        reference = cls._as_utc(now or datetime.now(UTC))
        current_week = reference.date() - timedelta(days=reference.weekday())
        week_starts = [current_week - timedelta(weeks=offset) for offset in reversed(range(weeks))]
        completed_by_week = {week.isoformat(): 0 for week in week_starts}
        lead_times: list[float] = []
        cycle_times: list[float] = []
        for issue in issues:
            completed_at = issue.resolution_date
            if completed_at is None:
                continue
            completed_utc = cls._as_utc(completed_at)
            completed_week = completed_utc.date() - timedelta(days=completed_utc.date().weekday())
            key = completed_week.isoformat()
            if key in completed_by_week:
                completed_by_week[key] += 1
            if issue.created:
                lead_times.append(
                    max((completed_utc - cls._as_utc(issue.created)).total_seconds(), 0) / 86400
                )
            started_at = cls._work_started_at(histories.get(issue.key, []))
            if started_at:
                cycle_times.append(max((completed_utc - started_at).total_seconds(), 0) / 86400)
        return {
            "project_key": project_key,
            "weeks": weeks,
            "completed_by_week": completed_by_week,
            "completed_count": sum(completed_by_week.values()),
            "average_lead_time_days": cls._average(lead_times),
            "average_cycle_time_days": cls._average(cycle_times),
            "lead_time_sample_size": len(lead_times),
            "cycle_time_sample_size": len(cycle_times),
        }

    @classmethod
    def sprint_performance(
        cls,
        sprint: dict,
        issues: list[Ticket],
        histories: dict[str, list[dict]],
    ) -> dict[str, object]:
        sprint_id = int(sprint["id"])
        sprint_name = str(sprint.get("name") or sprint_id)
        start = cls._parse_datetime(sprint.get("startDate"))
        completed = [issue for issue in issues if cls.is_completed(issue)]
        points_available = any(issue.story_points is not None for issue in issues)
        added: list[str] = []
        removed: list[str] = []
        carryover: list[str] = []
        for issue in issues:
            sprint_changes = cls._sprint_changes(
                histories.get(issue.key, []), sprint_id, sprint_name
            )
            if any(
                change[1] == "added" and (start is None or change[0] > start)
                for change in sprint_changes
            ):
                added.append(issue.key)
            if any(
                change[1] == "removed" and (start is None or change[0] > start)
                for change in sprint_changes
            ):
                removed.append(issue.key)
            if any(change[1] == "added" and change[2] for change in sprint_changes):
                carryover.append(issue.key)
        current_keys = {issue.key for issue in issues}
        for issue_key, issue_histories in histories.items():
            if issue_key in current_keys:
                continue
            sprint_changes = cls._sprint_changes(issue_histories, sprint_id, sprint_name)
            if any(
                change[1] == "removed" and (start is None or change[0] > start)
                for change in sprint_changes
            ):
                removed.append(issue_key)
        return {
            "sprint_id": sprint_id,
            "sprint_name": sprint_name,
            "throughput": len(completed),
            "committed_issue_count": len(issues) - len(added) + len(removed),
            "completed_story_points": (
                round(sum(issue.story_points or 0 for issue in completed), 2)
                if points_available
                else None
            ),
            "committed_story_points": (
                round(sum(issue.story_points or 0 for issue in issues), 2)
                if points_available
                else None
            ),
            "scope_added_issue_keys": added,
            "scope_removed_issue_keys": removed,
            "carryover_issue_keys": carryover,
        }

    @classmethod
    def _work_started_at(cls, histories: list[dict]) -> datetime | None:
        candidates = []
        for history in histories:
            created = cls._parse_datetime(history.get("created"))
            for item in history.get("items") or []:
                target = str(item.get("toString") or "").casefold()
                if (
                    item.get("field") == "status"
                    and target
                    and target not in cls._not_started_statuses
                    and created
                ):
                    candidates.append(created)
        return min(candidates) if candidates else None

    @classmethod
    def _sprint_changes(cls, histories, sprint_id, sprint_name):
        changes = []
        markers = {str(sprint_id).casefold(), sprint_name.casefold()}
        for history in histories:
            created = cls._parse_datetime(history.get("created"))
            if created is None:
                continue
            for item in history.get("items") or []:
                if str(item.get("field") or "").casefold() != "sprint":
                    continue
                before = str(item.get("fromString") or "").casefold()
                after = str(item.get("toString") or "").casefold()
                was_present = any(marker in before for marker in markers)
                is_present = any(marker in after for marker in markers)
                if is_present and not was_present:
                    changes.append((created, "added", bool(before)))
                elif was_present and not is_present:
                    changes.append((created, "removed", False))
        return changes

    @staticmethod
    def _parse_datetime(value) -> datetime | None:
        if not value or not isinstance(value, str):
            return None
        return AnalyticsService._as_utc(datetime.fromisoformat(value.replace("Z", "+00:00")))

    @staticmethod
    def _average(values: list[float]) -> float | None:
        return round(sum(values) / len(values), 2) if values else None

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    @staticmethod
    def _counts(values: Iterable[str]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for value in values:
            counts[value] = counts.get(value, 0) + 1
        return counts

    @staticmethod
    def _matrix(
        issues: list[Ticket],
        row_value: Callable[[Ticket], str],
        column_value: Callable[[Ticket], str],
    ) -> dict[str, dict[str, int]]:
        matrix: dict[str, dict[str, int]] = {}
        for issue in issues:
            row = row_value(issue)
            column = column_value(issue)
            row_counts = matrix.setdefault(row, {})
            row_counts[column] = row_counts.get(column, 0) + 1
        return matrix
