"""Direct Jira read and search endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import (
    AdminDependency,
    DatabaseSessionDependency,
    IssueAccessDependency,
    JiraServiceDependency,
    ProjectAccessDependency,
    ProjectKeyPath,
    SprintAccessDependency,
    ViewerDependency,
)
from app.core.config import Settings, get_settings
from app.models.ticket import Ticket
from app.schemas.project import ProjectSchema
from app.schemas.search import IssueSearchQuery, IssueSearchResponse
from app.services.access_service import AccessService

router = APIRouter(tags=["Jira"])


@router.get("/client-config", response_model=dict[str, str])
def get_client_configuration(settings: Annotated[Settings, Depends(get_settings)]):
    """Expose only non-secret browser configuration."""
    return {"jira_base_url": str(settings.jira_base_url).rstrip("/")}


@router.get("/")
def home():
    return {"message": "Jira AI Intelligence API is running"}


@router.get("/projects", response_model=list[ProjectSchema])
def get_projects(
    user: ViewerDependency,
    database: DatabaseSessionDependency,
):
    """Return synchronized projects authorized for the current user."""
    return [
        {"id": project.jira_id, "key": project.key, "name": project.name}
        for project in AccessService(database).list_accessible_projects(user)
    ]


@router.get("/boards")
def get_boards(_admin: AdminDependency, jira_service: JiraServiceDependency):
    return jira_service.get_boards()


@router.get("/sprints/{board_id}")
def get_sprints(
    board_id: int,
    _admin: AdminDependency,
    jira_service: JiraServiceDependency,
):
    return jira_service.get_sprints(board_id)


@router.get("/sprints/{sprint_id}/issues", response_model=list[Ticket])
def get_sprint_issues(
    sprint_id: int,
    _access: SprintAccessDependency,
    jira_service: JiraServiceDependency,
):
    return jira_service.get_sprint_issues(sprint_id)


@router.get("/users")
def get_users(_admin: AdminDependency, jira_service: JiraServiceDependency):
    return jira_service.get_users()


@router.get("/issues/{project_key}/search", response_model=IssueSearchResponse)
def search_project_issues(
    project_key: ProjectKeyPath,
    _access: ProjectAccessDependency,
    jira_service: JiraServiceDependency,
    query: Annotated[IssueSearchQuery, Depends()],
):
    if (
        query.created_from is not None
        and query.created_to is not None
        and query.created_from > query.created_to
    ):
        raise HTTPException(
            status_code=422,
            detail="created_from must be before or equal to created_to.",
        )
    return jira_service.search_project_issues(project_key, query)


@router.get("/issues/detail/{issue_key}", response_model=Ticket)
def get_issue_detail(
    issue_key: str,
    _access: IssueAccessDependency,
    jira_service: JiraServiceDependency,
):
    return jira_service.get_issue(issue_key)


@router.get("/issues/{issue_key}/comments")
def get_issue_comments(
    issue_key: str,
    _access: IssueAccessDependency,
    jira_service: JiraServiceDependency,
):
    return jira_service.get_comments(issue_key)


@router.get("/issues/{project_key}", response_model=list[Ticket])
def get_project_issues(
    project_key: ProjectKeyPath,
    _access: ProjectAccessDependency,
    jira_service: JiraServiceDependency,
):
    issues = jira_service.get_project_issues(project_key)
    if not issues:
        raise HTTPException(
            status_code=404,
            detail=f"No issues found for project '{project_key}'.",
        )
    return issues
