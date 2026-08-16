"""Deprecated live-Jira diagnostics; product views use synchronized stored data."""

from fastapi import APIRouter, HTTPException, Query

from app.api.dependencies import (
    JiraServiceDependency,
    ProjectAccessDependency,
    ProjectKeyPath,
    SprintAccessDependency,
)
from app.schemas.analytics import (
    OverdueIssuesSchema,
    ProjectActivitySchema,
    ProjectHistorySchema,
    ProjectInsightsSchema,
    ProjectOverviewSchema,
    ProjectSprintSummarySchema,
    SprintCompletionSchema,
    SprintPerformanceSchema,
)

router = APIRouter(
    prefix="/analytics",
    tags=["live Jira diagnostics"],
    deprecated=True,
)


@router.get("/projects/{project_key}/history", response_model=ProjectHistorySchema)
def get_project_history_metrics(
    project_key: ProjectKeyPath,
    _access: ProjectAccessDependency,
    jira_service: JiraServiceDependency,
    weeks: int = Query(default=8, ge=1, le=52),
):
    metrics = jira_service.get_project_history_metrics(project_key, weeks)
    if metrics is None:
        raise HTTPException(404, f"No issues found for project '{project_key}'.")
    return metrics


@router.get("/projects/{project_key}/insights", response_model=ProjectInsightsSchema)
def get_project_insights(
    project_key: ProjectKeyPath,
    _access: ProjectAccessDependency,
    jira_service: JiraServiceDependency,
    weeks: int = Query(default=8, ge=1, le=52),
):
    insights = jira_service.get_project_insights(project_key, weeks)
    if insights is None:
        raise HTTPException(404, f"No issues found for project '{project_key}'.")
    return insights


@router.get("/projects/{project_key}/activity", response_model=ProjectActivitySchema)
def get_project_activity(
    project_key: ProjectKeyPath,
    _access: ProjectAccessDependency,
    jira_service: JiraServiceDependency,
    stale_days: int = Query(default=14, ge=1, le=365),
    limit: int = Query(default=5, ge=1, le=50),
):
    activity = jira_service.get_project_activity(project_key, stale_days, limit)
    if activity is None:
        raise HTTPException(404, f"No issues found for project '{project_key}'.")
    return activity


@router.get("/projects/{project_key}/overview", response_model=ProjectOverviewSchema)
def get_project_overview(
    project_key: ProjectKeyPath,
    _access: ProjectAccessDependency,
    jira_service: JiraServiceDependency,
):
    overview = jira_service.get_project_overview(project_key)
    if overview is None:
        raise HTTPException(404, f"No issues found for project '{project_key}'.")
    return overview


def _require_counts(counts: dict[str, int], project_key: str) -> dict[str, int]:
    if not counts:
        raise HTTPException(404, f"No issues found for project '{project_key}'.")
    return counts


@router.get("/projects/{project_key}/status-counts", response_model=dict[str, int])
def get_issue_status_counts(
    project_key: ProjectKeyPath,
    _access: ProjectAccessDependency,
    jira_service: JiraServiceDependency,
):
    return _require_counts(jira_service.get_issue_status_counts(project_key), project_key)


@router.get("/projects/{project_key}/workload", response_model=dict[str, int])
def get_workload_by_assignee(
    project_key: ProjectKeyPath,
    _access: ProjectAccessDependency,
    jira_service: JiraServiceDependency,
):
    return _require_counts(jira_service.get_workload_by_assignee(project_key), project_key)


@router.get("/projects/{project_key}/priority-counts", response_model=dict[str, int])
def get_issue_priority_counts(
    project_key: ProjectKeyPath,
    _access: ProjectAccessDependency,
    jira_service: JiraServiceDependency,
):
    return _require_counts(jira_service.get_issue_priority_counts(project_key), project_key)


@router.get("/projects/{project_key}/type-counts", response_model=dict[str, int])
def get_issue_type_counts(
    project_key: ProjectKeyPath,
    _access: ProjectAccessDependency,
    jira_service: JiraServiceDependency,
):
    return _require_counts(jira_service.get_issue_type_counts(project_key), project_key)


@router.get("/sprints/{sprint_id}/performance", response_model=SprintPerformanceSchema)
def get_sprint_performance(
    sprint_id: int,
    _access: SprintAccessDependency,
    jira_service: JiraServiceDependency,
):
    performance = jira_service.get_sprint_performance(sprint_id)
    if performance is None:
        raise HTTPException(404, f"No issues found for sprint '{sprint_id}'.")
    return performance


@router.get("/projects/{project_key}/sprints", response_model=ProjectSprintSummarySchema)
def get_project_sprint_summary(
    project_key: ProjectKeyPath,
    _access: ProjectAccessDependency,
    jira_service: JiraServiceDependency,
):
    result = jira_service.get_project_sprint_summary(project_key)
    if result is None:
        raise HTTPException(404, f"No sprints found for project '{project_key}'.")
    return result


@router.get("/sprints/{sprint_id}/completion", response_model=SprintCompletionSchema)
def get_sprint_completion(
    sprint_id: int,
    _access: SprintAccessDependency,
    jira_service: JiraServiceDependency,
):
    completion = jira_service.get_sprint_completion(sprint_id)
    if completion["total"] == 0:
        raise HTTPException(404, f"No issues found for sprint '{sprint_id}'.")
    return completion


@router.get("/projects/{project_key}/overdue", response_model=OverdueIssuesSchema)
def get_overdue_issues(
    project_key: ProjectKeyPath,
    _access: ProjectAccessDependency,
    jira_service: JiraServiceDependency,
):
    overdue_summary = jira_service.get_overdue_summary(project_key)
    if overdue_summary is None:
        raise HTTPException(404, f"No issues found for project '{project_key}'.")
    return overdue_summary
