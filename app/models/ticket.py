from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field


class Ticket(BaseModel):
    id: str | None = None
    key: str
    summary: str | None = None
    description: dict[str, Any] | str | None = None
    status: str | None = None
    status_category: str | None = None
    priority: str | None = None
    issue_type: str | None = None
    assignee: str | None = None
    reporter: str | None = None
    created: datetime | None = None
    updated: datetime | None = None
    resolution_date: datetime | None = None
    due_date: date | None = None
    story_points: float | None = None
    labels: list[str] = Field(default_factory=list)
