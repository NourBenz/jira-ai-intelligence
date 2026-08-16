"""Validated request and response models for prototype authentication."""

from typing import Literal

from pydantic import BaseModel, Field

UserRole = Literal["viewer", "admin"]


class LoginRequest(BaseModel):
    username: str = Field(
        min_length=3,
        max_length=100,
        pattern=r"^[A-Za-z0-9_.@-]+$",
    )
    password: str = Field(min_length=8, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in_seconds: int


class CurrentUserResponse(BaseModel):
    id: int
    username: str
    first_name: str | None
    last_name: str | None
    email: str | None
    role: UserRole
    administered_project_keys: list[str]
