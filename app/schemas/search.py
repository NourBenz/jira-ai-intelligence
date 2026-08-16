from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

from app.models.ticket import Ticket


class IssueSearchQuery(BaseModel):
    status: str | None = Field(default=None, min_length=1, max_length=100)
    assignee: str | None = Field(default=None, min_length=1, max_length=100)
    priority: str | None = Field(default=None, min_length=1, max_length=100)
    issue_type: str | None = Field(default=None, min_length=1, max_length=100)
    label: str | None = Field(default=None, min_length=1, max_length=100)
    created_from: date | None = None
    created_to: date | None = None
    sort_by: Literal["created", "updated", "duedate", "priority", "key"] = "created"
    order: Literal["asc", "desc"] = "desc"
    limit: int = Field(default=20, ge=1, le=100)
    page_token: str | None = Field(default=None, max_length=2000)


class IssueSearchResponse(BaseModel):
    project_key: str
    issues: list[Ticket]
    returned: int
    is_last: bool
    next_page_token: str | None = None
