"""Authentication and role-based authorization tests."""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_rag_service
from app.core.config import Settings, get_settings
from app.core.rate_limit import InMemoryRateLimiter, rate_limiter
from app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from app.database import (
    Base,
    ProjectEntity,
    SyncRunEntity,
    TeamEntity,
    TeamMembershipEntity,
    UserEntity,
)
from app.database.session import (
    create_database_engine,
    get_database_session,
)
from app.schemas.rag import RAGIndexResponse
from main import app

TEST_SETTINGS = Settings(
    _env_file=None,
    jira_base_url="https://example.atlassian.net",
    jira_email="developer@example.com",
    jira_api_token="not-a-real-jira-token",
    jwt_secret_key="test-jwt-secret-key-with-at-least-32-characters",
    jwt_access_token_minutes=30,
)


class FakeRAGService:
    def index_project(self, project_key):
        return RAGIndexResponse(
            project_key=project_key,
            issues_processed=1,
            chunks_indexed=1,
            embedding_model="fake-embedding",
        )


@pytest.fixture
def auth_client():
    rate_limiter.clear()
    engine = create_database_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        viewer = UserEntity(
            username="viewer",
            first_name="Nour",
            last_name="Viewer",
            email="viewer@example.com",
            password_hash=hash_password("viewer-password"),
            role="viewer",
            is_active=True,
            created_at=datetime.now(UTC),
        )
        admin = UserEntity(
            username="admin",
            password_hash=hash_password("admin-password"),
            role="admin",
            is_active=True,
            created_at=datetime.now(UTC),
        )
        team = TeamEntity(
            name="T1 Scrum Team",
            description="Authorization test team",
            is_active=True,
            created_at=datetime.now(UTC),
        )
        project = ProjectEntity(jira_id="10000", key="T1", name="T1", owning_team=team)
        session.add_all([viewer, admin, team, project])
        session.flush()
        session.add(
            TeamMembershipEntity(
                user=viewer,
                team=team,
                scrum_role="developer",
                is_active=True,
                joined_at=datetime.now(UTC),
            )
        )
        session.commit()

    def database_override():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_database_session] = database_override
    app.dependency_overrides[get_settings] = lambda: TEST_SETTINGS
    app.dependency_overrides[get_rag_service] = FakeRAGService
    client = TestClient(app)
    client.test_engine = engine
    try:
        yield client
    finally:
        app.dependency_overrides.clear()
        rate_limiter.clear()


def login(client: TestClient, username: str, password: str) -> str:
    response = client.post(
        "/api/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def test_password_hash_is_not_plaintext_and_verifies():
    encoded = hash_password("safe-password")

    assert encoded != "safe-password"
    assert verify_password("safe-password", encoded)
    assert not verify_password("wrong-password", encoded)
    assert not verify_password("safe-password", "not-a-valid-hash")


def test_anonymous_business_route_is_rejected(auth_client):
    response = auth_client.get("/api/projects")

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_login_returns_token_and_me_returns_identity(auth_client):
    token = login(auth_client, "viewer", "viewer-password")

    response = auth_client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["username"] == "viewer"
    assert response.json()["first_name"] == "Nour"
    assert response.json()["last_name"] == "Viewer"
    assert response.json()["email"] == "viewer@example.com"
    assert response.json()["role"] == "viewer"


def test_team_member_can_check_shared_project_freshness(auth_client):
    completed_at = datetime.now(UTC)
    with Session(auth_client.test_engine) as session:
        project = session.scalar(select(ProjectEntity).where(ProjectEntity.key == "T1"))
        project.jira_checked_at = completed_at
        session.add(
            SyncRunEntity(
                project_key="T1",
                mode="incremental",
                status="completed",
                started_at=completed_at,
                completed_at=completed_at,
            )
        )
        session.commit()

    token = login(auth_client, "viewer", "viewer-password")
    response = auth_client.get(
        "/api/sync/projects/T1/freshness",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["project_key"] == "T1"
    assert response.json()["last_completed_sync_id"] == 1
    assert response.json()["completed_at"] is not None
    assert set(response.json()) == {
        "project_key",
        "last_completed_sync_id",
        "completed_at",
        "sync_required",
        "jira_checked_at",
        "jira_latest_issue_key",
        "jira_latest_updated_at",
        "update_check_error",
    }


def test_login_failure_uses_generic_message(auth_client):
    unknown = auth_client.post(
        "/api/auth/login",
        json={"username": "unknown", "password": "wrong-password"},
    )
    wrong_password = auth_client.post(
        "/api/auth/login",
        json={"username": "viewer", "password": "wrong-password"},
    )

    assert unknown.status_code == 401
    assert wrong_password.status_code == 401
    assert unknown.json() == wrong_password.json()


def test_expired_token_is_rejected(auth_client):
    token, _ = create_access_token(
        1,
        "viewer",
        TEST_SETTINGS,
        now=datetime.now(UTC) - timedelta(hours=1),
    )

    response = auth_client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401


def test_malformed_token_is_rejected(auth_client):
    response = auth_client.get(
        "/api/auth/me",
        headers={"Authorization": "Bearer definitely-not-a-jwt"},
    )

    assert response.status_code == 401


def test_disabled_user_cannot_continue_using_existing_token(auth_client):
    token = login(auth_client, "viewer", "viewer-password")
    with Session(auth_client.test_engine) as session:
        user = session.query(UserEntity).filter_by(username="viewer").one()
        user.is_active = False
        session.commit()

    response = auth_client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401


def test_database_role_change_invalidates_existing_token(auth_client):
    token = login(auth_client, "viewer", "viewer-password")
    with Session(auth_client.test_engine) as session:
        user = session.query(UserEntity).filter_by(username="viewer").one()
        user.role = "admin"
        session.commit()

    response = auth_client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401


@pytest.mark.parametrize(
    "path",
    [
        "/api/rag/projects/T1/index",
        "/api/sync/projects/T1",
        "/api/sync/projects/T1/incremental",
    ],
)
def test_viewer_cannot_run_privileged_operations(auth_client, path):
    token = login(auth_client, "viewer", "viewer-password")

    response = auth_client.post(
        path,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Project administrator access is required."


def test_admin_can_rebuild_rag_index(auth_client):
    token = login(auth_client, "admin", "admin-password")

    response = auth_client.post(
        "/api/rag/projects/T1/index",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["chunks_indexed"] == 1


def test_rate_limiter_rejects_request_over_limit():
    limiter = InMemoryRateLimiter()
    limiter.check("user:1", limit=2, window_seconds=60, now=100.0)
    limiter.check("user:1", limit=2, window_seconds=60, now=101.0)

    with pytest.raises(HTTPException) as error:
        limiter.check("user:1", limit=2, window_seconds=60, now=102.0)

    assert error.value.status_code == 429
    assert error.value.headers["Retry-After"] == "58"


def test_rate_limiter_allows_requests_after_window_expires():
    limiter = InMemoryRateLimiter()
    limiter.check("user:1", limit=1, window_seconds=60, now=100.0)

    limiter.check("user:1", limit=1, window_seconds=60, now=161.0)


def test_cors_allows_configured_origin_and_rejects_unknown(auth_client):
    allowed = auth_client.options(
        "/api/projects",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    rejected = auth_client.options(
        "/api/projects",
        headers={
            "Origin": "https://untrusted.example",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert allowed.status_code == 200
    assert allowed.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert rejected.status_code == 400
    assert "access-control-allow-origin" not in rejected.headers
