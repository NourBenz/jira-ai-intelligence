"""Database-backed Jira and analytics endpoints."""

from fastapi import APIRouter, HTTPException, Query

from app.api.dependencies import (
    DatabaseSessionDependency,
    ProjectAccessDependency,
    ProjectKeyPath,
    SprintAccessDependency,
)
from app.models.ticket import Ticket
from app.schemas.analytics import (
    ProjectActivitySchema,
    ProjectHistorySchema,
    ProjectInsightsSchema,
    ProjectOverviewSchema,
    ProjectRiskAnalysisSchema,
    ProjectSprintSummarySchema,
    SprintPerformanceSchema,
)
from app.services.stored_data_service import StoredDataService

router = APIRouter(prefix="/stored", tags=["stored data"])


@router.get(
    "/analytics/projects/{project_key}/sprints",
    response_model=ProjectSprintSummarySchema,
)
def get_stored_project_sprints(
    project_key: ProjectKeyPath,
    _access: ProjectAccessDependency,
    database: DatabaseSessionDependency,
):
    """Return synchronized sprint membership without contacting Jira."""
    result = StoredDataService(database).get_project_sprint_summary(project_key)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"No stored sprints found for project '{project_key}'.",
        )
    return result


@router.get("/sprints/{sprint_id}/issues", response_model=list[Ticket])
def get_stored_sprint_issues(
    sprint_id: int,
    _access: SprintAccessDependency,
    database: DatabaseSessionDependency,
):
    """Return synchronized issue membership for one sprint."""
    issues = StoredDataService(database).get_sprint_issues(sprint_id)
    if issues is None:
        raise HTTPException(
            status_code=404,
            detail=f"No stored sprint found for sprint '{sprint_id}'.",
        )
    return issues


@router.get("/issues/{project_key}", response_model=list[Ticket])
def get_stored_project_issues(
    project_key: ProjectKeyPath,
    _access: ProjectAccessDependency,
    database: DatabaseSessionDependency,
):
    issues = StoredDataService(database).get_project_issues(project_key)
    if not issues:
        raise HTTPException(
            status_code=404,
            detail=f"No stored issues found for project '{project_key}'.",
        )
    return issues


@router.get(
    "/analytics/projects/{project_key}/overview",
    response_model=ProjectOverviewSchema,
)
def get_stored_project_overview(
    project_key: ProjectKeyPath,
    _access: ProjectAccessDependency,
    database: DatabaseSessionDependency,
):
    result = StoredDataService(database).get_project_overview(project_key)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"No stored issues found for project '{project_key}'.",
        )
    return result


@router.get(
    "/analytics/projects/{project_key}/activity",
    response_model=ProjectActivitySchema,
)
def get_stored_project_activity(
    project_key: ProjectKeyPath,
    _access: ProjectAccessDependency,
    database: DatabaseSessionDependency,
    stale_days: int = Query(default=14, ge=1, le=365),
    limit: int = Query(default=5, ge=1, le=50),
):
    result = StoredDataService(database).get_project_activity(project_key, stale_days, limit)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"No stored issues found for project '{project_key}'.",
        )
    return result


@router.get(
    "/analytics/projects/{project_key}/insights",
    response_model=ProjectInsightsSchema,
)
def get_stored_project_insights(
    project_key: ProjectKeyPath,
    _access: ProjectAccessDependency,
    database: DatabaseSessionDependency,
    weeks: int = Query(default=8, ge=1, le=52),
):
    result = StoredDataService(database).get_project_insights(project_key, weeks)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"No stored issues found for project '{project_key}'.",
        )
    return result


@router.get(
    "/analytics/projects/{project_key}/history",
    response_model=ProjectHistorySchema,
)
def get_stored_project_history(
    project_key: ProjectKeyPath,
    _access: ProjectAccessDependency,
    database: DatabaseSessionDependency,
    weeks: int = Query(default=8, ge=1, le=52),
):
    result = StoredDataService(database).get_project_history(project_key, weeks)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"No stored issues found for project '{project_key}'.",
        )
    return result


@router.get(
    "/analytics/projects/{project_key}/risks",
    response_model=ProjectRiskAnalysisSchema,
)
def get_stored_project_risks(
    project_key: ProjectKeyPath,
    _access: ProjectAccessDependency,
    database: DatabaseSessionDependency,
):
    """Return delivery risks from the shared deterministic rule engine."""
    result = StoredDataService(database).get_project_risks(project_key)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"No stored issues found for project '{project_key}'.",
        )
    return result


@router.get(
    "/analytics/sprints/{sprint_id}/performance",
    response_model=SprintPerformanceSchema,
)
def get_stored_sprint_performance(
    sprint_id: int,
    _access: SprintAccessDependency,
    database: DatabaseSessionDependency,
):
    result = StoredDataService(database).get_sprint_performance(sprint_id)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"No stored issues found for sprint '{sprint_id}'.",
        )
    return result
