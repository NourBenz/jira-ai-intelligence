"""Company-admin endpoints for Scrum teams and project access assignments."""

from fastapi import APIRouter, Depends, Response, status

from app.api.dependencies import (
    AdminDependency,
    DatabaseSessionDependency,
    JiraServiceDependency,
    ProjectKeyPath,
    require_admin,
)
from app.schemas.access import (
    AccessUserResponse,
    ProjectAccessSummaryResponse,
    ProjectAdministratorRequest,
    ProjectTeamRequest,
    TeamCreateRequest,
    TeamMemberResponse,
    TeamMembershipRequest,
    TeamResponse,
)
from app.schemas.project import ProjectSchema
from app.services.access_service import AccessService

router = APIRouter(
    prefix="/admin",
    tags=["access administration"],
    dependencies=[Depends(require_admin)],
)


@router.get("/jira/projects", response_model=list[ProjectSchema])
def discover_jira_projects(jira_service: JiraServiceDependency):
    """Show Jira projects only to a company administrator for onboarding."""
    return jira_service.get_projects()


@router.get("/access/users", response_model=list[AccessUserResponse])
def list_application_users(database: DatabaseSessionDependency):
    return AccessService(database).list_users()


@router.get("/access/teams", response_model=list[TeamResponse])
def list_teams(database: DatabaseSessionDependency):
    return AccessService(database).list_teams()


@router.post("/access/teams", response_model=TeamResponse, status_code=status.HTTP_201_CREATED)
def create_team(request: TeamCreateRequest, database: DatabaseSessionDependency):
    return AccessService(database).create_team(request.name, request.description)


@router.post(
    "/access/teams/{team_id}/members",
    status_code=status.HTTP_204_NO_CONTENT,
)
def assign_team_member(
    team_id: int,
    request: TeamMembershipRequest,
    database: DatabaseSessionDependency,
):
    AccessService(database).assign_user_to_team(team_id, request.user_id, request.scrum_role)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete(
    "/access/teams/{team_id}/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_team_member(team_id: int, user_id: int, database: DatabaseSessionDependency):
    AccessService(database).remove_user_from_team(team_id, user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put(
    "/access/projects/{project_key}/team",
    status_code=status.HTTP_204_NO_CONTENT,
)
def assign_project_team(
    project_key: ProjectKeyPath,
    request: ProjectTeamRequest,
    database: DatabaseSessionDependency,
):
    AccessService(database).assign_project_team(project_key, request.team_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/access/projects/{project_key}/administrators",
    status_code=status.HTTP_204_NO_CONTENT,
)
def grant_project_administrator(
    project_key: ProjectKeyPath,
    request: ProjectAdministratorRequest,
    company_admin: AdminDependency,
    database: DatabaseSessionDependency,
):
    AccessService(database).grant_project_administrator(
        project_key,
        request.user_id,
        company_admin,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete(
    "/access/projects/{project_key}/administrators/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def revoke_project_administrator(
    project_key: ProjectKeyPath,
    user_id: int,
    database: DatabaseSessionDependency,
):
    AccessService(database).revoke_project_administrator(project_key, user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/access/projects/{project_key}",
    response_model=ProjectAccessSummaryResponse,
)
def get_project_access(project_key: ProjectKeyPath, database: DatabaseSessionDependency):
    project = AccessService(database).project_access_summary(project_key)
    team = project.owning_team
    members = []
    if team is not None:
        for link in team.member_links:
            user = link.user
            if not link.is_active:
                continue
            display_name = (
                " ".join(part for part in (user.first_name, user.last_name) if part)
                or user.username
            )
            members.append(
                TeamMemberResponse(
                    user_id=user.id,
                    username=user.username,
                    display_name=display_name,
                    scrum_role=link.scrum_role,
                    is_active=user.is_active,
                )
            )
    return ProjectAccessSummaryResponse(
        project_key=project.key,
        project_name=project.name,
        owning_team=(
            TeamResponse(
                id=team.id,
                name=team.name,
                description=team.description,
                is_active=team.is_active,
                created_at=team.created_at,
            )
            if team is not None
            else None
        ),
        team_members=members,
        project_administrator_ids=[
            link.user_id for link in project.administrator_links if link.is_active
        ],
    )
