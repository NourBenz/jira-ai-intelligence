"""Project isolation tests for one company with multiple Scrum teams."""

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.dependencies import get_rag_service
from app.core.config import Settings, get_settings
from app.core.rate_limit import rate_limiter
from app.core.security import hash_password
from app.database import (
    Base,
    IssueEntity,
    ProjectAdministratorEntity,
    ProjectEntity,
    TeamEntity,
    TeamMembershipEntity,
    UserEntity,
)
from app.database.session import create_database_engine, get_database_session
from app.schemas.rag import RAGIndexResponse
from main import app

TEST_SETTINGS = Settings(
    _env_file=None,
    jira_base_url="https://example.atlassian.net",
    jira_email="developer@example.com",
    jira_api_token="not-a-real-jira-token",
    jwt_secret_key="project-access-tests-need-a-long-secret-key",
)


class FakeRAGService:
    def index_project(self, project_key: str):
        return RAGIndexResponse(
            project_key=project_key,
            issues_processed=1,
            chunks_indexed=1,
            embedding_model="fake-embedding",
        )


@pytest.fixture
def access_client():
    rate_limiter.clear()
    engine = create_database_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    now = datetime.now(UTC)
    with Session(engine) as session:
        admin = _user("company-admin", "admin", now)
        team_x_user = _user("team-x-user", "viewer", now)
        team_y_user = _user("team-y-user", "viewer", now)
        project_admin = _user("t2-project-admin", "viewer", now)
        team_x = TeamEntity(name="Team X", is_active=True, created_at=now)
        team_y = TeamEntity(name="Team Y", is_active=True, created_at=now)
        t1 = ProjectEntity(jira_id="10001", key="T1", name="Team X Project", owning_team=team_x)
        t2 = ProjectEntity(jira_id="10002", key="T2", name="Team Y Project", owning_team=team_y)
        t1.issues.append(_issue("11001", "T1-1", "Team X evidence"))
        t2.issues.append(_issue("12001", "T2-1", "Team Y evidence"))
        session.add_all([admin, team_x_user, team_y_user, project_admin, t1, t2])
        session.flush()
        session.add_all(
            [
                TeamMembershipEntity(
                    user=team_x_user,
                    team=team_x,
                    scrum_role="developer",
                    is_active=True,
                    joined_at=now,
                ),
                TeamMembershipEntity(
                    user=team_y_user,
                    team=team_y,
                    scrum_role="developer",
                    is_active=True,
                    joined_at=now,
                ),
                ProjectAdministratorEntity(
                    user=project_admin,
                    project=t2,
                    granted_by=admin,
                    is_active=True,
                    granted_at=now,
                ),
            ]
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


def _user(username: str, role: str, now: datetime) -> UserEntity:
    return UserEntity(
        username=username,
        password_hash=hash_password("safe-password"),
        role=role,
        is_active=True,
        created_at=now,
    )


def _issue(jira_id: str, key: str, summary: str) -> IssueEntity:
    return IssueEntity(
        jira_id=jira_id,
        key=key,
        summary=summary,
        status="To Do",
        status_category="To Do",
        labels=[],
    )


def _headers(client: TestClient, username: str) -> dict[str, str]:
    response = client.post(
        "/api/auth/login",
        json={"username": username, "password": "safe-password"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_team_members_list_only_their_owning_teams_projects(access_client):
    team_x = access_client.get("/api/projects", headers=_headers(access_client, "team-x-user"))
    team_y = access_client.get("/api/projects", headers=_headers(access_client, "team-y-user"))
    company_admin = access_client.get(
        "/api/projects", headers=_headers(access_client, "company-admin")
    )

    assert [project["key"] for project in team_x.json()] == ["T1"]
    assert [project["key"] for project in team_y.json()] == ["T2"]
    assert {project["key"] for project in company_admin.json()} == {"T1", "T2"}


def test_team_member_cannot_read_or_search_another_projects_data(access_client):
    headers = _headers(access_client, "team-x-user")

    own = access_client.get("/api/stored/issues/T1", headers=headers)
    other = access_client.get("/api/stored/issues/T2", headers=headers)
    rag = access_client.post(
        "/api/rag/projects/T2/search",
        headers=headers,
        json={"query": "Team Y evidence", "top_k": 3},
    )

    assert own.status_code == 200
    assert other.status_code == 404
    assert other.json()["detail"] == "Project is not available."
    assert rag.status_code == 404


def test_project_administrator_can_only_administer_the_assigned_project(access_client):
    headers = _headers(access_client, "t2-project-admin")

    identity = access_client.get("/api/auth/me", headers=headers)
    allowed = access_client.post("/api/rag/projects/T2/index", headers=headers)
    denied = access_client.post("/api/rag/projects/T1/index", headers=headers)

    assert identity.json()["administered_project_keys"] == ["T2"]
    assert allowed.status_code == 200
    assert denied.status_code == 403


def test_removing_team_membership_revokes_access_immediately(access_client):
    headers = _headers(access_client, "team-x-user")
    with Session(access_client.test_engine) as session:
        membership = (
            session.query(TeamMembershipEntity)
            .join(UserEntity)
            .filter(UserEntity.username == "team-x-user")
            .one()
        )
        membership.is_active = False
        session.commit()

    assert access_client.get("/api/projects", headers=headers).json() == []
    assert access_client.get("/api/stored/issues/T1", headers=headers).status_code == 404


def test_only_company_admin_can_manage_teams(access_client):
    denied = access_client.get(
        "/api/admin/access/teams",
        headers=_headers(access_client, "team-x-user"),
    )
    created = access_client.post(
        "/api/admin/access/teams",
        headers=_headers(access_client, "company-admin"),
        json={"name": "Platform Team", "description": "Shared infrastructure"},
    )

    assert denied.status_code == 403
    assert created.status_code == 201
    assert created.json()["name"] == "Platform Team"


def test_company_admin_can_assign_team_membership_and_project_administrator(access_client):
    admin_headers = _headers(access_client, "company-admin")
    with Session(access_client.test_engine) as session:
        team_y_id = session.query(TeamEntity.id).filter(TeamEntity.name == "Team Y").scalar()
        team_x_user_id = (
            session.query(UserEntity.id).filter(UserEntity.username == "team-x-user").scalar()
        )
        project_admin_id = (
            session.query(UserEntity.id).filter(UserEntity.username == "t2-project-admin").scalar()
        )

    membership = access_client.post(
        f"/api/admin/access/teams/{team_y_id}/members",
        headers=admin_headers,
        json={"user_id": team_x_user_id, "scrum_role": "qa"},
    )
    summary = access_client.get(
        "/api/admin/access/projects/T2",
        headers=admin_headers,
    )
    revoked = access_client.delete(
        f"/api/admin/access/projects/T2/administrators/{project_admin_id}",
        headers=admin_headers,
    )

    assert membership.status_code == 204
    assert any(
        member["username"] == "team-x-user" and member["scrum_role"] == "qa"
        for member in summary.json()["team_members"]
    )
    assert project_admin_id in summary.json()["project_administrator_ids"]
    assert revoked.status_code == 204
    assert (
        access_client.post(
            "/api/rag/projects/T2/index",
            headers=_headers(access_client, "t2-project-admin"),
        ).status_code
        == 403
    )


def test_malicious_project_key_is_rejected_before_jira_access(access_client):
    response = access_client.get(
        "/api/issues/T1%22%20OR%20project%20%3D%20%22T2",
        headers=_headers(access_client, "company-admin"),
    )

    assert response.status_code == 422
