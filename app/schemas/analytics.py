from pydantic import BaseModel

from app.models.ticket import Ticket


class SprintCompletionSchema(BaseModel):
    sprint_id: int
    total: int
    done: int
    remaining: int
    completion_rate: float


class OverdueIssuesSchema(BaseModel):
    total: int
    issues: list[Ticket]


class ProjectOverviewSchema(BaseModel):
    project_key: str
    total_issues: int
    status_counts: dict[str, int]
    priority_counts: dict[str, int]
    issue_type_counts: dict[str, int]
    workload_by_assignee: dict[str, int]
    overdue_count: int
    unassigned_count: int
    completed_count: int
    open_count: int
    completion_rate: float


class ProjectActivitySchema(BaseModel):
    project_key: str
    average_issue_age_days: float
    oldest_open_issues: list[Ticket]
    recently_updated_issues: list[Ticket]
    stale_days: int
    stale_issues: list[Ticket]


class ProjectInsightsSchema(BaseModel):
    project_key: str
    weeks: int
    created_by_week: dict[str, int]
    label_counts: dict[str, int]
    workload_by_assignee_status: dict[str, dict[str, int]]
    workload_by_assignee_priority: dict[str, dict[str, int]]
    overdue_by_assignee: dict[str, int]
    overdue_by_priority: dict[str, int]
    blocked_count: int
    blocked_issues: list[Ticket]


class ProjectHistorySchema(BaseModel):
    project_key: str
    weeks: int
    completed_by_week: dict[str, int]
    completed_count: int
    average_lead_time_days: float | None
    average_cycle_time_days: float | None
    lead_time_sample_size: int
    cycle_time_sample_size: int


class SprintPerformanceSchema(BaseModel):
    sprint_id: int
    sprint_name: str
    throughput: int
    committed_issue_count: int
    completed_story_points: float | None
    committed_story_points: float | None
    scope_added_issue_keys: list[str]
    scope_removed_issue_keys: list[str]
    carryover_issue_keys: list[str]


class SprintSummaryItemSchema(BaseModel):
    sprint_id: int
    board_id: int
    name: str
    state: str
    start_date: str | None
    end_date: str | None
    issue_count: int
    completed_count: int
    open_count: int
    completion_rate: float


class ProjectSprintSummarySchema(BaseModel):
    project_key: str
    total_sprints: int
    sprints: list[SprintSummaryItemSchema]


class RiskSignalSchema(BaseModel):
    type: str
    label: str
    severity: str
    fact: str
    issue_keys: list[str]
    recommended_action: str


class ProjectRiskAnalysisSchema(BaseModel):
    project_key: str
    signals: list[RiskSignalSchema]
    limitations: list[str]
