"""Tests for deterministic evidence supplied to the AI layer."""

from datetime import UTC, date, datetime, timedelta

from app.models.ticket import Ticket
from app.services.evidence_service import EvidenceService


class FakeStoredData:
    def __init__(self, issues, overview, activity, insights, history=None):
        self.issues = issues
        self.overview = overview
        self.activity = activity
        self.insights = insights
        self.history = history or {"completed_count": 0}

    def get_project_issues(self, project_key):
        return self.issues

    def get_project_overview(self, project_key):
        return self.overview

    def get_project_activity(self, project_key, stale_days, limit):
        assert (stale_days, limit) == (14, 10)
        return self.activity

    def get_project_insights(self, project_key, weeks):
        assert weeks == 8
        return self.insights

    def get_project_history(self, project_key, weeks):
        assert weeks == 8
        return self.history


def test_evidence_returns_none_when_project_has_no_stored_issues():
    stored = FakeStoredData([], {}, {}, {})

    assert EvidenceService(stored).build_project_evidence("EMPTY") is None


def test_evidence_builds_each_supported_delivery_risk():
    old_update = datetime.now(UTC) - timedelta(days=30)
    issues = [
        Ticket(key="T1-1", status_category="To Do", assignee="Alice"),
        Ticket(
            key="T1-2",
            status_category="To Do",
            assignee="Alice",
            due_date=date.today() - timedelta(days=1),
        ),
        Ticket(
            key="T1-3",
            status_category="To Do",
            assignee="Alice",
            updated=old_update,
        ),
        Ticket(key="T1-4", status_category="To Do", assignee=None),
        Ticket(key="T1-5", status_category="To Do", assignee="Bob"),
        Ticket(key="T1-6", status_category="Done", assignee="Alice"),
    ]
    stored = FakeStoredData(
        issues,
        {
            "total_issues": 6,
            "open_count": 5,
            "completion_rate": 16.67,
        },
        {
            "average_issue_age_days": 20.0,
            "stale_issues": [issues[2]],
        },
        {
            "workload_by_assignee_status": {},
            "overdue_by_assignee": {"Alice": 1},
            "blocked_issues": [issues[0]],
        },
    )

    evidence = EvidenceService(stored).build_project_evidence("T1")

    assert evidence is not None
    assert [signal["type"] for signal in evidence["risk_signals"]] == [
        "blocked_work",
        "overdue_work",
        "stale_work",
        "unassigned_work",
        "workload_concentration",
        "low_completion",
    ]
    assert evidence["issue_state_context"]["completed_issue_keys"] == ["T1-6"]
    assert evidence["activity"]["stale_issue_keys"] == ["T1-3"]
    assert evidence["insights"]["blocked_issue_keys"] == ["T1-1"]
    assert "No issue due dates are available." not in evidence["known_limitations"]
    assert "No story-point estimates are available." in evidence["known_limitations"]
    assert "No issue labels are available." in evidence["known_limitations"]


def test_evidence_reports_missing_fields_without_inventing_risks():
    issue = Ticket(
        key="T1-1",
        summary="Small healthy backlog",
        status_category="To Do",
        assignee="Alice",
    )
    stored = FakeStoredData(
        [issue],
        {"total_issues": 1, "open_count": 1, "completion_rate": 0.0},
        {"average_issue_age_days": 1.0, "stale_issues": []},
        {
            "workload_by_assignee_status": {"Alice": {"To Do": 1}},
            "overdue_by_assignee": {},
            "blocked_issues": [],
        },
    )

    evidence = EvidenceService(stored).build_project_evidence("T1")

    assert evidence is not None
    assert evidence["risk_signals"] == []
    assert evidence["known_limitations"] == [
        "No issue due dates are available.",
        "No story-point estimates are available.",
        "No issue labels are available.",
    ]
    assert evidence["issues"] == [
        {
            "key": "T1-1",
            "summary": "Small healthy backlog",
            "status": None,
            "status_category": "To Do",
            "priority": None,
            "assignee": "Alice",
        }
    ]
