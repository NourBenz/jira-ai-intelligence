from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SyncRunSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    project_key: str
    mode: str
    status: str
    started_at: datetime
    completed_at: datetime | None
    projects_processed: int
    issues_processed: int
    sprints_processed: int
    changelogs_processed: int
    comments_processed: int
    error_message: str | None


class SyncChangeSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    issue_key: str
    change_type: str
    changed_fields: list[str]
    before_values: dict
    after_values: dict
    changelogs_inspected: int
    comments_inspected: int


class SyncRunDetailSchema(SyncRunSchema):
    changes: list[SyncChangeSchema]


class SyncFreshnessSchema(BaseModel):
    """Minimal shared state used by dashboards to detect a completed sync."""

    project_key: str
    last_completed_sync_id: int | None
    completed_at: datetime | None
    sync_required: bool
    jira_checked_at: datetime | None
    jira_latest_issue_key: str | None
    jira_latest_updated_at: datetime | None
    update_check_error: str | None
