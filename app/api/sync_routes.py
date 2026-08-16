"""Jira synchronization endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.dependencies import (
    DatabaseSessionDependency,
    JiraServiceDependency,
    ProjectAccessDependency,
    ProjectKeyPath,
    ViewerDependency,
    limit_admin_operation,
    require_project_administrator,
)
from app.database.repositories import JiraRepository
from app.schemas.sync import SyncFreshnessSchema, SyncRunDetailSchema, SyncRunSchema
from app.services.access_service import AccessService
from app.services.sync_observability_service import SyncObservabilityService
from app.services.sync_service import SyncService

router = APIRouter(prefix="/sync", tags=["synchronization"])


@router.post(
    "/projects/{project_key}",
    response_model=SyncRunSchema,
    dependencies=[Depends(require_project_administrator), Depends(limit_admin_operation)],
)
def sync_project(
    project_key: ProjectKeyPath,
    jira_service: JiraServiceDependency,
    database: DatabaseSessionDependency,
):
    return SyncService(database, jira_service).full_sync(project_key)


@router.post(
    "/projects/{project_key}/incremental",
    response_model=SyncRunSchema,
    dependencies=[Depends(require_project_administrator), Depends(limit_admin_operation)],
)
def incrementally_sync_project(
    project_key: ProjectKeyPath,
    jira_service: JiraServiceDependency,
    database: DatabaseSessionDependency,
):
    return SyncService(database, jira_service).incremental_sync(project_key)


@router.get(
    "/projects/{project_key}/freshness",
    response_model=SyncFreshnessSchema,
)
def get_sync_freshness(
    project_key: ProjectKeyPath,
    _access: ProjectAccessDependency,
    jira_service: JiraServiceDependency,
    database: DatabaseSessionDependency,
):
    """Return the shared sync marker and a cached Jira update check."""
    project = SyncObservabilityService(database, jira_service).check(project_key)
    run = JiraRepository(database).last_successful_sync(project_key)
    return SyncFreshnessSchema(
        project_key=project_key,
        last_completed_sync_id=run.id if run is not None else None,
        completed_at=run.completed_at if run is not None else None,
        sync_required=project.jira_updates_available,
        jira_checked_at=project.jira_checked_at,
        jira_latest_issue_key=project.jira_latest_issue_key,
        jira_latest_updated_at=project.jira_latest_updated_at,
        update_check_error=project.jira_update_check_error,
    )


@router.post(
    "/projects/{project_key}/check",
    response_model=SyncFreshnessSchema,
    dependencies=[Depends(require_project_administrator), Depends(limit_admin_operation)],
)
def check_project_updates(
    project_key: ProjectKeyPath,
    jira_service: JiraServiceDependency,
    database: DatabaseSessionDependency,
):
    """Force a Jira freshness check for an authorized project administrator."""
    project = SyncObservabilityService(database, jira_service).check(project_key, force=True)
    run = JiraRepository(database).last_successful_sync(project_key)
    return SyncFreshnessSchema(
        project_key=project_key,
        last_completed_sync_id=run.id if run is not None else None,
        completed_at=run.completed_at if run is not None else None,
        sync_required=project.jira_updates_available,
        jira_checked_at=project.jira_checked_at,
        jira_latest_issue_key=project.jira_latest_issue_key,
        jira_latest_updated_at=project.jira_latest_updated_at,
        update_check_error=project.jira_update_check_error,
    )


@router.get("/runs", response_model=list[SyncRunSchema])
def list_sync_runs(
    database: DatabaseSessionDependency,
    user: ViewerDependency,
    limit: int = Query(default=20, ge=1, le=100),
):
    keys = None
    if user.role != "admin":
        keys = {project.key for project in AccessService(database).list_accessible_projects(user)}
    return JiraRepository(database).list_sync_runs(limit, keys)


@router.get("/runs/{run_id}", response_model=SyncRunDetailSchema)
def get_sync_run(
    run_id: int,
    database: DatabaseSessionDependency,
    user: ViewerDependency,
):
    run = JiraRepository(database).get_sync_run_with_changes(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Synchronization run not found.")
    if not AccessService(database).can_access_project(user, run.project_key):
        raise HTTPException(status_code=404, detail="Synchronization run not found.")
    return run
