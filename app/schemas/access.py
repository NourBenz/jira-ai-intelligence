"""Validated models for Scrum teams and project-scoped access administration."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

ScrumRole = Literal["developer", "product_owner", "scrum_master", "qa", "other"]


class TeamCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    description: str | None = Field(default=None, max_length=500)


class TeamResponse(BaseModel):
    id: int
    name: str
    description: str | None
    is_active: bool
    created_at: datetime


class TeamMembershipRequest(BaseModel):
    user_id: int = Field(gt=0)
    scrum_role: ScrumRole | None = None


class ProjectTeamRequest(BaseModel):
    team_id: int = Field(gt=0)


class ProjectAdministratorRequest(BaseModel):
    user_id: int = Field(gt=0)


class AccessUserResponse(BaseModel):
    id: int
    username: str
    first_name: str | None
    last_name: str | None
    email: str | None
    role: str
    is_active: bool


class TeamMemberResponse(BaseModel):
    user_id: int
    username: str
    display_name: str
    scrum_role: str | None
    is_active: bool


class ProjectAccessSummaryResponse(BaseModel):
    project_key: str
    project_name: str
    owning_team: TeamResponse | None
    team_members: list[TeamMemberResponse]
    project_administrator_ids: list[int]
