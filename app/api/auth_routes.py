"""Public login and authenticated identity endpoints."""

from typing import Annotated, cast

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from app.api.dependencies import (
    CurrentUserDependency,
    DatabaseSessionDependency,
    limit_login,
)
from app.core.config import Settings, get_settings
from app.core.security import (
    DUMMY_PASSWORD_HASH,
    create_access_token,
    verify_password,
)
from app.database.entities import UserEntity
from app.schemas.auth import (
    CurrentUserResponse,
    LoginRequest,
    TokenResponse,
    UserRole,
)
from app.services.access_service import AccessService

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post(
    "/login",
    response_model=TokenResponse,
    dependencies=[Depends(limit_login)],
)
def login(
    request: LoginRequest,
    database: DatabaseSessionDependency,
    settings: Annotated[Settings, Depends(get_settings)],
):
    user = database.scalar(select(UserEntity).where(UserEntity.username == request.username))
    password_matches = verify_password(
        request.password,
        user.password_hash if user is not None else DUMMY_PASSWORD_HASH,
    )
    if user is None or not password_matches or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token, ttl = create_access_token(user.id, user.role, settings)
    return TokenResponse(access_token=token, expires_in_seconds=ttl)


@router.get("/me", response_model=CurrentUserResponse)
def current_user(user: CurrentUserDependency, database: DatabaseSessionDependency):
    return CurrentUserResponse(
        id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        email=user.email,
        role=cast(UserRole, user.role),
        administered_project_keys=AccessService(database).list_administered_project_keys(user),
    )
