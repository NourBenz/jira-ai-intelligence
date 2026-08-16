"""Tests for API endpoints."""

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.dependencies import (
    get_jira_service,
    get_rag_service,
    limit_admin_operation,
    limit_ai_request,
    require_admin,
    require_viewer,
)
from app.core.config import Settings, get_settings
from app.database import Base, ProjectEntity
from app.database.session import create_database_engine, get_database_session
from app.schemas.rag import RAGAnswerResponse, RAGIndexResponse, RAGSearchResponse
from main import app, get_readiness_settings

API_TEST_SETTINGS = Settings(
    _env_file=None,
    jira_base_url="https://example.atlassian.net",
    jira_email="developer@example.com",
    jira_api_token="not-a-real-jira-token",
    jwt_secret_key="test-jwt-secret-key-with-at-least-32-characters",
)


@pytest.fixture(autouse=True)
def authenticated_api_user():
    """Keep existing route tests focused on their original behavior."""
    user = SimpleNamespace(id=1, username="tester", role="admin")
    engine = create_database_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    def database_override():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[require_viewer] = lambda: user
    app.dependency_overrides[require_admin] = lambda: user
    app.dependency_overrides[limit_ai_request] = lambda: None
    app.dependency_overrides[limit_admin_operation] = lambda: None
    app.dependency_overrides[get_settings] = lambda: API_TEST_SETTINGS
    app.dependency_overrides[get_readiness_settings] = lambda: API_TEST_SETTINGS
    app.dependency_overrides[get_database_session] = database_override
    yield
    app.dependency_overrides.clear()


class FakeJiraService:
    """Small service replacement used only by API tests."""

    def get_projects(self) -> list[dict[str, str]]:
        return [
            {
                "id": "10000",
                "key": "TEST",
                "name": "Test Project",
            }
        ]

    def search_project_issues(self, project_key, query):
        return {
            "project_key": project_key,
            "issues": [],
            "returned": 0,
            "is_last": True,
            "next_page_token": None,
        }

    def get_project_sprint_summary(self, project_key):
        return {
            "project_key": project_key,
            "total_sprints": 1,
            "sprints": [
                {
                    "sprint_id": 69,
                    "board_id": 34,
                    "name": "T1 Sprint 3",
                    "state": "active",
                    "start_date": None,
                    "end_date": None,
                    "issue_count": 5,
                    "completed_count": 1,
                    "open_count": 4,
                    "completion_rate": 20.0,
                }
            ],
        }


def test_get_projects_endpoint_uses_authorized_stored_projects():
    engine = create_database_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(ProjectEntity(jira_id="10000", key="TEST", name="Test Project"))
        session.commit()

    def database_override():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_database_session] = database_override

    try:
        response = TestClient(app).get("/api/projects")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": "10000",
            "key": "TEST",
            "name": "Test Project",
        }
    ]


def test_client_configuration_exposes_only_safe_jira_url():
    response = TestClient(app).get("/api/client-config")

    assert response.status_code == 200
    assert response.json() == {"jira_base_url": "https://example.atlassian.net"}
    assert "token" not in response.text.lower()


def test_health_does_not_create_jira_service():
    def fail_if_called():
        raise AssertionError("Jira service must not be created")

    app.dependency_overrides[get_jira_service] = fail_if_called
    try:
        response = TestClient(app).get("/health")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_readiness_validates_configuration():
    response = TestClient(app).get("/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_issue_search_validates_and_uses_injected_service():
    app.dependency_overrides[get_jira_service] = FakeJiraService
    try:
        response = TestClient(app).get(
            "/api/issues/T1/search",
            params={
                "status": "To Do",
                "sort_by": "updated",
                "order": "asc",
                "limit": 10,
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["project_key"] == "T1"
    assert response.json()["is_last"] is True


def test_issue_search_rejects_invalid_options_before_jira():
    app.dependency_overrides[get_jira_service] = FakeJiraService
    try:
        bad_sort = TestClient(app).get("/api/issues/T1/search?sort_by=summary")
        bad_dates = TestClient(app).get(
            "/api/issues/T1/search?created_from=2026-07-12&created_to=2026-07-01"
        )
    finally:
        app.dependency_overrides.clear()

    assert bad_sort.status_code == 422
    assert bad_dates.status_code == 422


def test_project_sprint_summary_endpoint_uses_injected_service():
    app.dependency_overrides[get_jira_service] = FakeJiraService
    try:
        response = TestClient(app).get("/api/analytics/projects/T1/sprints")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["total_sprints"] == 1
    assert response.json()["sprints"][0]["issue_count"] == 5


class FakeRAGService:
    def index_project(self, project_key):
        return RAGIndexResponse(
            project_key=project_key,
            issues_processed=2,
            chunks_indexed=3,
            embedding_model="fake-embedding",
        )

    def search(self, project_key, query, top_k):
        return RAGSearchResponse(
            project_key=project_key,
            query=query,
            results=[],
            returned=0,
            embedding_model="fake-embedding",
        )

    def ask(self, project_key, question):
        return RAGAnswerResponse(
            project_key=project_key,
            model="fake-local-model",
            answer="T1-22 describes AI hallucinating missing tickets.",
            source_issue_keys=["T1-22"],
            limitations=[],
            retrieved_chunks=10,
        )


def test_rag_index_endpoint_uses_injected_service():
    app.dependency_overrides[get_rag_service] = FakeRAGService
    try:
        response = TestClient(app).post("/api/rag/projects/T1/index")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["chunks_indexed"] == 3


def test_rag_search_endpoint_validates_body_and_uses_injected_service():
    app.dependency_overrides[get_rag_service] = FakeRAGService
    try:
        response = TestClient(app).post(
            "/api/rag/projects/T1/search",
            json={"query": "authentication problem", "top_k": 3},
        )
        invalid = TestClient(app).post(
            "/api/rag/projects/T1/search",
            json={"query": "x", "top_k": 100},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["query"] == "authentication problem"
    assert invalid.status_code == 422


def test_rag_answer_endpoint_validates_body_and_uses_injected_service():
    app.dependency_overrides[get_rag_service] = FakeRAGService
    try:
        response = TestClient(app).post(
            "/api/rag/projects/T1/ask",
            json={"question": "Which issue describes invented Jira tickets?"},
        )
        invalid = TestClient(app).post(
            "/api/rag/projects/T1/ask",
            json={"question": "x"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["source_issue_keys"] == ["T1-22"]
    assert response.json()["grounded"] is True
    assert invalid.status_code == 422


def test_rag_routes_return_not_found_when_project_has_no_evidence():
    class MissingRAGService(FakeRAGService):
        def index_project(self, project_key):
            return None

        def ask(self, project_key, question):
            return None

    app.dependency_overrides[get_rag_service] = MissingRAGService
    try:
        index_response = TestClient(app).post("/api/rag/projects/EMPTY/index")
        ask_response = TestClient(app).post(
            "/api/rag/projects/EMPTY/ask",
            json={"question": "What issue explains this behavior?"},
        )
    finally:
        app.dependency_overrides.clear()

    assert index_response.status_code == 404
    assert ask_response.status_code == 404


def test_ai_route_returns_not_found_without_stored_project_evidence():
    engine = create_database_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    def database_override():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_database_session] = database_override
    try:
        response = TestClient(app).post(
            "/api/ai/projects/EMPTY/ask",
            json={"question": "What are the delivery risks?"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
