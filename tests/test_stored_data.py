from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.dependencies import (
    get_jira_service,
    require_project_access,
    require_sprint_access,
    require_viewer,
)
from app.database import (
    Base,
    ChangelogEntity,
    CommentEntity,
    IssueEntity,
    ProjectEntity,
    SprintEntity,
    SprintIssueEntity,
)
from app.database.session import create_database_engine, get_database_session
from app.services.stored_data_service import StoredDataService
from main import app


@pytest.fixture(autouse=True)
def authenticated_stored_data_user():
    user = SimpleNamespace(id=1, username="tester", role="viewer")
    app.dependency_overrides[require_viewer] = lambda: user
    app.dependency_overrides[require_project_access] = lambda: user
    app.dependency_overrides[require_sprint_access] = lambda: user
    yield
    app.dependency_overrides.clear()


def _seeded_session():
    engine = create_database_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = Session(engine)
    project = ProjectEntity(jira_id="10000", key="T1", name="T1")
    project.issues.extend(
        [
            IssueEntity(
                jira_id="10001",
                key="T1-1",
                summary="Stored open issue",
                status="To Do",
                status_category="To Do",
                priority="High",
                issue_type="Task",
                assignee="Alice",
                labels=["backend"],
                created_at=datetime(2026, 7, 1, tzinfo=UTC),
                updated_at=datetime(2026, 7, 2, tzinfo=UTC),
            ),
            IssueEntity(
                jira_id="10002",
                key="T1-2",
                summary="Stored completed issue",
                status="Done",
                status_category="Done",
                priority="Medium",
                issue_type="Bug",
                assignee=None,
                labels=[],
                created_at=datetime(2026, 7, 1, tzinfo=UTC),
                updated_at=datetime(2026, 7, 3, tzinfo=UTC),
            ),
        ]
    )
    session.add(project)
    session.commit()
    return session


def test_stored_service_builds_overview_from_database():
    with _seeded_session() as session:
        result = StoredDataService(session).get_project_overview("T1")

        assert result["total_issues"] == 2
        assert result["completed_count"] == 1
        assert result["workload_by_assignee"] == {"Alice": 1, "Unassigned": 1}
        assert result["unassigned_count"] == 0


def test_stored_risks_use_the_same_open_issue_rules_as_overview():
    with _seeded_session() as session:
        result = StoredDataService(session).get_project_risks("T1")

        assert result is not None
        assert "unassigned_work" not in {signal["type"] for signal in result["signals"]}
        assert "No issue due dates are available." in result["limitations"]


def test_stored_service_exact_issue_lookup_is_project_scoped():
    with _seeded_session() as session:
        service = StoredDataService(session)

        issue = service.get_project_issue("T1", "T1-1")

        assert issue is not None
        assert issue.summary == "Stored open issue"
        assert service.get_project_issue("OTHER", "T1-1") is None
        assert service.get_project_issue("T1", "T1-999") is None


def test_stored_endpoint_does_not_construct_jira_service():
    session = _seeded_session()

    def database_override():
        yield session

    def jira_must_not_be_called():
        raise AssertionError("Stored endpoint must not contact Jira")

    app.dependency_overrides[get_database_session] = database_override
    app.dependency_overrides[get_jira_service] = jira_must_not_be_called
    try:
        response = TestClient(app).get("/api/stored/analytics/projects/T1/overview")
    finally:
        app.dependency_overrides.clear()
        session.close()

    assert response.status_code == 200
    assert response.json()["total_issues"] == 2


def test_stored_issues_endpoint_returns_not_found_for_unknown_project():
    engine = create_database_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    def database_override():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_database_session] = database_override
    try:
        response = TestClient(app).get("/api/stored/issues/EMPTY")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404


def test_stored_history_and_sprint_performance_use_database():
    with _seeded_session() as session:
        project = session.query(ProjectEntity).filter_by(key="T1").one()
        issue = session.query(IssueEntity).filter_by(key="T1-2").one()
        sprint = SprintEntity(
            jira_id=69,
            project=project,
            board_id=34,
            name="T1 Sprint 3",
            state="active",
        )
        session.add(sprint)
        session.flush()
        session.add(SprintIssueEntity(sprint=sprint, issue=issue))
        session.add(
            ChangelogEntity(
                issue=issue,
                jira_history_id="90001",
                changed_at=datetime(2026, 7, 3, tzinfo=UTC),
                items=[{"field": "status", "toString": "Done"}],
            )
        )
        session.commit()

        history = StoredDataService(session).get_project_history("T1", 8)
        performance = StoredDataService(session).get_sprint_performance(69)
        sprint_summary = StoredDataService(session).get_project_sprint_summary("T1")

        assert history["project_key"] == "T1"
        assert performance["sprint_id"] == 69
        assert performance["throughput"] == 1
        assert sprint_summary["total_sprints"] == 1
        assert sprint_summary["sprints"][0]["name"] == "T1 Sprint 3"
        assert sprint_summary["sprints"][0]["issue_count"] == 1
        assert sprint_summary["sprints"][0]["completed_count"] == 1


def test_stored_sprint_routes_return_synchronized_data_without_jira():
    session = _seeded_session()
    project = session.query(ProjectEntity).filter_by(key="T1").one()
    issue = session.query(IssueEntity).filter_by(key="T1-1").one()
    sprint = SprintEntity(
        jira_id=70,
        project=project,
        board_id=34,
        name="T1 Active Sprint",
        state="active",
    )
    session.add(sprint)
    session.flush()
    session.add(SprintIssueEntity(sprint=sprint, issue=issue))
    session.commit()

    def database_override():
        yield session

    def jira_must_not_be_called():
        raise AssertionError("Stored sprint endpoints must not contact Jira")

    app.dependency_overrides[get_database_session] = database_override
    app.dependency_overrides[get_jira_service] = jira_must_not_be_called
    try:
        client = TestClient(app)
        summary = client.get("/api/stored/analytics/projects/T1/sprints")
        issues = client.get("/api/stored/sprints/70/issues")
    finally:
        app.dependency_overrides.clear()
        session.close()

    assert summary.status_code == 200
    assert summary.json()["sprints"][0]["name"] == "T1 Active Sprint"
    assert issues.status_code == 200
    assert [issue["key"] for issue in issues.json()] == ["T1-1"]


def test_stored_sprint_route_returns_empty_list_for_known_empty_sprint():
    session = _seeded_session()
    project = session.query(ProjectEntity).filter_by(key="T1").one()
    session.add(
        SprintEntity(
            jira_id=71,
            project=project,
            board_id=34,
            name="T1 Future Sprint",
            state="future",
        )
    )
    session.commit()

    def database_override():
        yield session

    app.dependency_overrides[get_database_session] = database_override
    try:
        response = TestClient(app).get("/api/stored/sprints/71/issues")
    finally:
        app.dependency_overrides.clear()
        session.close()

    assert response.status_code == 200
    assert response.json() == []


def test_stored_service_returns_persisted_project_comments():
    with _seeded_session() as session:
        issue = session.query(IssueEntity).filter_by(key="T1-1").one()
        session.add(
            CommentEntity(
                issue=issue,
                jira_id="70001",
                author_name="Alice",
                body={
                    "type": "doc",
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": "OAuth token expired."}],
                        }
                    ],
                },
                created_at=datetime(2026, 7, 4, tzinfo=UTC),
                updated_at=datetime(2026, 7, 5, tzinfo=UTC),
            )
        )
        session.commit()

        comments = StoredDataService(session).get_project_comments("T1")

        assert list(comments) == ["T1-1"]
        assert comments["T1-1"][0]["id"] == "70001"
        assert comments["T1-1"][0]["author"] == "Alice"
        assert comments["T1-1"][0]["body"]["type"] == "doc"
