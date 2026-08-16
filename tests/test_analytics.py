"""Tests for analytics"""

from datetime import UTC, date, datetime, timedelta

from app.jira.jira_client import JiraClient
from app.models.ticket import Ticket
from app.services.analytics_service import AnalyticsService
from app.services.jira_service import JiraService


def test_overdue_summary_fetches_project_issues_once(monkeypatch):
    service = JiraService.__new__(JiraService)
    calls = 0
    tickets = [
        Ticket(
            key="TEST-1",
            due_date=date.today() - timedelta(days=1),
            status="To Do",
        ),
        Ticket(
            key="TEST-2",
            due_date=date.today() - timedelta(days=1),
            status="Done",
        ),
    ]

    def fake_get_project_issues(project_key: str) -> list[Ticket]:
        nonlocal calls
        calls += 1
        assert project_key == "TEST"
        return tickets

    monkeypatch.setattr(
        service,
        "get_project_issues",
        fake_get_project_issues,
    )

    result = service.get_overdue_summary("TEST")

    assert calls == 1
    assert result is not None
    assert result["total"] == 1
    assert result["issues"] == [tickets[0]]


def test_overdue_summary_distinguishes_no_issues(monkeypatch):
    service = JiraService.__new__(JiraService)
    monkeypatch.setattr(service, "get_project_issues", lambda _: [])

    assert service.get_overdue_summary("EMPTY") is None


def test_workload_by_assignee(monkeypatch):
    tickets = [
        Ticket(
            key="TEST-1",
            assignee="Alice",
        ),
        Ticket(
            key="TEST-2",
            assignee="Alice",
        ),
        Ticket(
            key="TEST-3",
            assignee=None,
        ),
    ]

    service = JiraService.__new__(JiraService)

    monkeypatch.setattr(
        service,
        "get_project_issues",
        lambda project_key: tickets,
    )

    result = service.get_workload_by_assignee("TEST")

    assert result == {
        "Alice": 2,
        "Unassigned": 1,
    }


def test_issue_status_counts(monkeypatch):
    tickets = [
        Ticket(
            key="TEST-1",
            status="To Do",
        ),
        Ticket(
            key="TEST-2",
            status="To Do",
        ),
        Ticket(
            key="TEST-3",
            status="Done",
        ),
        Ticket(
            key="TEST-4",
            status=None,
        ),
    ]

    service = JiraService.__new__(JiraService)

    monkeypatch.setattr(
        service,
        "get_project_issues",
        lambda project_key: tickets,
    )

    result = service.get_issue_status_counts("TEST")

    assert result == {
        "To Do": 2,
        "Done": 1,
        "Unknown": 1,
    }


def test_issue_priority_counts(monkeypatch):
    tickets = [
        Ticket(
            key="TEST-1",
            priority="High",
        ),
        Ticket(
            key="TEST-2",
            priority="High",
        ),
        Ticket(
            key="TEST-3",
            priority="Medium",
        ),
        Ticket(
            key="TEST-4",
            priority=None,
        ),
    ]

    service = JiraService.__new__(JiraService)

    monkeypatch.setattr(
        service,
        "get_project_issues",
        lambda project_key: tickets,
    )

    result = service.get_issue_priority_counts("TEST")

    assert result == {
        "High": 2,
        "Medium": 1,
        "None": 1,
    }


def test_issue_type_counts(monkeypatch):
    tickets = [
        Ticket(
            key="TEST-1",
            issue_type="Task",
        ),
        Ticket(
            key="TEST-2",
            issue_type="Task",
        ),
        Ticket(
            key="TEST-3",
            issue_type="Story",
        ),
        Ticket(
            key="TEST-4",
            issue_type=None,
        ),
    ]

    service = JiraService.__new__(JiraService)

    monkeypatch.setattr(
        service,
        "get_project_issues",
        lambda project_key: tickets,
    )

    result = service.get_issue_type_counts("TEST")

    assert result == {
        "Task": 2,
        "Story": 1,
        "Unknown": 1,
    }


def test_sprint_completion(monkeypatch):
    tickets = [
        Ticket(
            key="TEST-1",
            status="Done",
        ),
        Ticket(
            key="TEST-2",
            status="Closed",
        ),
        Ticket(
            key="TEST-3",
            status="Resolved",
        ),
        Ticket(
            key="TEST-4",
            status="To Do",
        ),
        Ticket(
            key="TEST-5",
            status=None,
        ),
    ]

    service = JiraService.__new__(JiraService)

    monkeypatch.setattr(
        service,
        "get_sprint_issues",
        lambda sprint_id: tickets,
    )

    result = service.get_sprint_completion(42)

    assert result == {
        "sprint_id": 42,
        "total": 5,
        "done": 3,
        "remaining": 2,
        "completion_rate": 60.0,
    }


def test_custom_done_category_overrides_status_name(monkeypatch):
    tickets = [
        Ticket(
            key="TEST-1",
            status="Deployed to Production",
            status_category="Done",
        ),
        Ticket(
            key="TEST-2",
            status="Done-looking custom name",
            status_category="In Progress",
        ),
    ]
    service = JiraService.__new__(JiraService)
    monkeypatch.setattr(
        service,
        "get_sprint_issues",
        lambda _: tickets,
    )

    result = service.get_sprint_completion(42)

    assert result["done"] == 1
    assert result["remaining"] == 1


def test_done_category_excludes_issue_from_overdue(monkeypatch):
    tickets = [
        Ticket(
            key="TEST-1",
            status="Deployed",
            status_category="Done",
            due_date=date.today() - timedelta(days=1),
        )
    ]
    service = JiraService.__new__(JiraService)
    monkeypatch.setattr(
        service,
        "get_project_issues",
        lambda _: tickets,
    )

    assert service.get_overdue_issues("TEST") == []


def test_overdue_issue_filtering(monkeypatch):
    yesterday = date.today() - timedelta(days=1)
    tomorrow = date.today() + timedelta(days=1)

    tickets = [
        Ticket(
            key="TEST-1",
            status="To Do",
            due_date=yesterday,
        ),
        Ticket(
            key="TEST-2",
            status="Done",
            due_date=yesterday,
        ),
        Ticket(
            key="TEST-3",
            status="To Do",
            due_date=tomorrow,
        ),
        Ticket(
            key="TEST-4",
            status="To Do",
            due_date=None,
        ),
    ]

    service = JiraService.__new__(JiraService)

    monkeypatch.setattr(
        service,
        "get_project_issues",
        lambda project_key: tickets,
    )

    result = service.get_overdue_issues("TEST")

    assert result == [tickets[0]]


def test_status_analytics_include_more_than_fifty_issues(
    monkeypatch,
):
    client = JiraClient.__new__(JiraClient)
    service = JiraService.__new__(JiraService)
    service.client = client

    def raw_issue(number, status):
        return {
            "id": str(number),
            "key": f"TEST-{number}",
            "fields": {
                "summary": f"Issue {number}",
                "status": {"name": status},
            },
        }

    def fake_get(endpoint, params=None):
        if params.get("nextPageToken") is None:
            return {
                "isLast": False,
                "nextPageToken": "page-2",
                "issues": [raw_issue(number, "To Do") for number in range(1, 51)],
            }

        return {
            "isLast": True,
            "issues": [raw_issue(51, "Done")],
        }

    monkeypatch.setattr(client, "_get", fake_get)

    result = service.get_issue_status_counts("TEST")

    assert result == {
        "To Do": 50,
        "Done": 1,
    }


def test_project_overview_fetches_once(monkeypatch):
    service = JiraService.__new__(JiraService)
    calls = 0
    tickets = [
        Ticket(
            key="TEST-1",
            status="Released",
            status_category="Done",
            priority="High",
            issue_type="Bug",
            assignee="Alice",
            due_date=date.today() - timedelta(days=1),
        ),
        Ticket(
            key="TEST-2",
            status="To Do",
            status_category="To Do",
            priority=None,
            issue_type="Task",
            assignee=None,
            due_date=date.today() - timedelta(days=1),
        ),
    ]

    def fake_get_project_issues(project_key):
        nonlocal calls
        calls += 1
        return tickets

    monkeypatch.setattr(
        service,
        "get_project_issues",
        fake_get_project_issues,
    )

    result = service.get_project_overview("TEST")

    assert calls == 1
    assert result is not None
    assert result["total_issues"] == 2
    assert result["completed_count"] == 1
    assert result["open_count"] == 1
    assert result["overdue_count"] == 1
    assert result["unassigned_count"] == 1
    assert result["completion_rate"] == 50.0


def test_project_activity_metrics():
    now = datetime(2026, 7, 12, tzinfo=UTC)
    tickets = [
        Ticket(
            key="TEST-1",
            status_category="To Do",
            created=now - timedelta(days=30),
            updated=now - timedelta(days=20),
        ),
        Ticket(
            key="TEST-2",
            status_category="In Progress",
            created=now - timedelta(days=10),
            updated=now - timedelta(days=1),
        ),
        Ticket(
            key="TEST-3",
            status_category="Done",
            created=now - timedelta(days=20),
            updated=now,
        ),
    ]

    result = AnalyticsService.project_activity(
        "TEST",
        tickets,
        stale_days=14,
        limit=2,
        now=now,
    )

    assert result["average_issue_age_days"] == 20.0
    assert [issue.key for issue in result["oldest_open_issues"]] == [
        "TEST-1",
        "TEST-2",
    ]
    assert [issue.key for issue in result["recently_updated_issues"]] == [
        "TEST-3",
        "TEST-2",
    ]
    assert [issue.key for issue in result["stale_issues"]] == ["TEST-1"]


def test_project_insights_metrics():
    now = datetime(2026, 7, 12, tzinfo=UTC)
    tickets = [
        Ticket(
            key="TEST-1",
            status="Blocked",
            priority="High",
            assignee="Alice",
            created=datetime(2026, 7, 6, tzinfo=UTC),
            due_date=date(2026, 7, 10),
            labels=["backend", "blocked"],
        ),
        Ticket(
            key="TEST-2",
            status="In Progress",
            priority="Medium",
            assignee="Alice",
            created=datetime(2026, 6, 30, tzinfo=UTC),
            labels=["backend"],
        ),
        Ticket(
            key="TEST-3",
            status="Done",
            status_category="Done",
            priority=None,
            assignee=None,
            created=datetime(2026, 7, 7, tzinfo=UTC),
            due_date=date(2026, 7, 1),
            labels=[],
        ),
    ]

    result = AnalyticsService.project_insights("TEST", tickets, weeks=2, now=now)

    assert result["created_by_week"] == {
        "2026-06-29": 1,
        "2026-07-06": 2,
    }
    assert result["label_counts"] == {"backend": 2, "blocked": 1}
    assert result["workload_by_assignee_status"] == {
        "Alice": {"Blocked": 1, "In Progress": 1},
        "Unassigned": {"Done": 1},
    }
    assert result["workload_by_assignee_priority"] == {
        "Alice": {"High": 1, "Medium": 1},
        "Unassigned": {"None": 1},
    }
    assert result["overdue_by_assignee"] == {"Alice": 1}
    assert result["overdue_by_priority"] == {"High": 1}
    assert result["blocked_count"] == 1
    assert result["blocked_issues"] == [tickets[0]]


def test_project_insights_fetches_issues_once(monkeypatch):
    service = JiraService.__new__(JiraService)
    calls = 0

    def fake_get_project_issues(project_key):
        nonlocal calls
        calls += 1
        assert project_key == "TEST"
        return [Ticket(key="TEST-1")]

    monkeypatch.setattr(service, "get_project_issues", fake_get_project_issues)

    assert service.get_project_insights("TEST", 8) is not None
    assert calls == 1


def test_project_sprint_summary_counts_each_matching_project_sprint(monkeypatch):
    service = JiraService.__new__(JiraService)
    requested_sprints = []

    monkeypatch.setattr(
        service,
        "get_boards",
        lambda: {
            "values": [
                {"id": 34, "location": {"projectKey": "T1"}},
                {"id": 99, "location": {"projectKey": "OTHER"}},
            ]
        },
    )
    monkeypatch.setattr(
        service,
        "get_sprints",
        lambda board_id: {
            "values": [
                {
                    "id": 68,
                    "name": "T1 Sprint 2",
                    "state": "closed",
                    "startDate": "2026-08-03T00:00:00Z",
                    "endDate": "2026-09-04T00:00:00Z",
                },
                {
                    "id": 69,
                    "name": "T1 Sprint 3",
                    "state": "active",
                },
            ]
        },
    )

    def sprint_issues(sprint_id):
        requested_sprints.append(sprint_id)
        if sprint_id == 68:
            return [
                Ticket(key="T1-1", status_category="Done"),
                Ticket(key="T1-2", status_category="To Do"),
            ]
        return [Ticket(key="T1-3", status_category="To Do")]

    monkeypatch.setattr(service, "get_sprint_issues", sprint_issues)

    result = service.get_project_sprint_summary("T1")

    assert result["total_sprints"] == 2
    assert requested_sprints == [68, 69]
    assert result["sprints"][0]["issue_count"] == 2
    assert result["sprints"][0]["completed_count"] == 1
    assert result["sprints"][0]["completion_rate"] == 50.0
    assert result["sprints"][1]["open_count"] == 1


class TestMetrics:
    """Test metrics calculations"""

    def test_calculate_velocity(self):
        issues = [
            Ticket(key="TEST-1", status_category="Done", story_points=5),
            Ticket(key="TEST-2", status_category="To Do", story_points=3),
        ]
        result = AnalyticsService.sprint_performance({"id": 7, "name": "Sprint 7"}, issues, {})
        assert result["throughput"] == 1
        assert result["completed_story_points"] == 5
        assert result["committed_story_points"] == 8

    def test_calculate_cycle_time(self):
        created = datetime(2026, 7, 1, tzinfo=UTC)
        completed = datetime(2026, 7, 5, tzinfo=UTC)
        issues = [Ticket(key="TEST-1", created=created, resolution_date=completed)]
        histories = {
            "TEST-1": [
                {
                    "created": "2026-07-02T00:00:00Z",
                    "items": [{"field": "status", "toString": "In Progress"}],
                }
            ]
        }
        result = AnalyticsService.history_metrics(
            "TEST",
            issues,
            histories,
            weeks=1,
            now=datetime(2026, 7, 5, tzinfo=UTC),
        )
        assert result["average_lead_time_days"] == 4.0
        assert result["average_cycle_time_days"] == 3.0


def test_sprint_scope_changes_use_sprint_start():
    issues = [Ticket(key="TEST-1"), Ticket(key="TEST-2")]
    histories = {
        "TEST-1": [
            {
                "created": "2026-07-03T00:00:00Z",
                "items": [
                    {
                        "field": "Sprint",
                        "fromString": None,
                        "toString": "Sprint 7",
                    }
                ],
            }
        ],
        "TEST-2": [
            {
                "created": "2026-07-04T00:00:00Z",
                "items": [
                    {
                        "field": "Sprint",
                        "fromString": "Sprint 7",
                        "toString": None,
                    }
                ],
            }
        ],
    }
    result = AnalyticsService.sprint_performance(
        {
            "id": 7,
            "name": "Sprint 7",
            "startDate": "2026-07-02T00:00:00Z",
        },
        issues,
        histories,
    )
    assert result["scope_added_issue_keys"] == ["TEST-1"]
    assert result["scope_removed_issue_keys"] == ["TEST-2"]
