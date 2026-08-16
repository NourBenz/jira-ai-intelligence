"""Dependencies shared by API endpoints."""

from typing import Annotated

from fastapi import Depends, HTTPException, Path, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import AfterValidator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.ollama_client import OllamaClient
from app.core.config import Settings, get_settings
from app.core.rate_limit import rate_limiter
from app.core.security import decode_access_token
from app.database.entities import IssueEntity, ProjectEntity, SprintEntity, UserEntity
from app.database.session import get_database_session
from app.rag.embeddings import OllamaEmbeddingClient
from app.rag.vector_store import PgVectorStore
from app.services.access_service import AccessService
from app.services.jira_service import JiraService
from app.services.rag_service import RAGService
from app.services.stored_data_service import StoredDataService


def get_jira_service() -> JiraService:
    """Create the Jira service when an endpoint actually needs it."""
    return JiraService()


JiraServiceDependency = Annotated[
    JiraService,
    Depends(get_jira_service),
]

DatabaseSessionDependency = Annotated[
    Session,
    Depends(get_database_session),
]

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
    database: DatabaseSessionDependency,
    settings: Annotated[Settings, Depends(get_settings)],
) -> UserEntity:
    """Validate a bearer token and return its active database user."""
    authentication_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Valid authentication is required.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise authentication_error
    try:
        payload = decode_access_token(credentials.credentials, settings)
    except ValueError as error:
        raise authentication_error from error

    user = database.scalar(select(UserEntity).where(UserEntity.id == int(payload["sub"])))
    if user is None or not user.is_active or user.role != payload["role"]:
        raise authentication_error
    return user


CurrentUserDependency = Annotated[
    UserEntity,
    Depends(get_current_user),
]


def require_viewer(user: CurrentUserDependency) -> UserEntity:
    """Allow both read-only viewers and administrators."""
    if user.role not in {"viewer", "admin"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Viewer access is required.",
        )
    return user


def require_admin(user: CurrentUserDependency) -> UserEntity:
    """Allow only administrators to run privileged operations."""
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator access is required.",
        )
    return user


ViewerDependency = Annotated[
    UserEntity,
    Depends(require_viewer),
]

AdminDependency = Annotated[
    UserEntity,
    Depends(require_admin),
]

ProjectKeyPath = Annotated[
    str,
    AfterValidator(lambda value: value.upper()),
    Path(pattern=r"^[A-Za-z][A-Za-z0-9_-]{0,49}$"),
]


def require_project_access(
    project_key: ProjectKeyPath,
    user: Annotated[UserEntity, Depends(require_viewer)],
    database: DatabaseSessionDependency,
) -> UserEntity:
    """Allow company admins or users assigned through the project's Scrum team."""
    if not AccessService(database).can_access_project(user, project_key):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project is not available.",
        )
    return user


def require_project_administrator(
    project_key: ProjectKeyPath,
    user: Annotated[UserEntity, Depends(require_viewer)],
    database: DatabaseSessionDependency,
) -> UserEntity:
    """Allow company admins or an explicitly appointed project administrator."""
    if not AccessService(database).can_administer_project(user, project_key):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Project administrator access is required.",
        )
    return user


def require_sprint_access(
    sprint_id: Annotated[int, Path(gt=0)],
    user: Annotated[UserEntity, Depends(require_viewer)],
    database: DatabaseSessionDependency,
) -> UserEntity:
    """Resolve a synchronized sprint to its project before authorizing access."""
    if user.role == "admin":
        return user
    project_key = database.scalar(
        select(ProjectEntity.key)
        .join(SprintEntity, SprintEntity.project_id == ProjectEntity.id)
        .where(SprintEntity.jira_id == sprint_id)
    )
    if project_key is None or not AccessService(database).can_access_project(user, project_key):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Sprint is not available.")
    return user


def require_issue_access(
    issue_key: Annotated[str, Path(pattern=r"^[A-Za-z][A-Za-z0-9_-]{0,49}-[1-9][0-9]*$")],
    user: Annotated[UserEntity, Depends(require_viewer)],
    database: DatabaseSessionDependency,
) -> UserEntity:
    """Resolve a synchronized issue to its project before authorizing access."""
    if user.role == "admin":
        return user
    project_key = database.scalar(
        select(ProjectEntity.key)
        .join(IssueEntity, IssueEntity.project_id == ProjectEntity.id)
        .where(IssueEntity.key == issue_key.upper())
    )
    if project_key is None or not AccessService(database).can_access_project(user, project_key):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Issue is not available.")
    return user


ProjectAccessDependency = Annotated[
    UserEntity,
    Depends(require_project_access),
]

ProjectAdministratorDependency = Annotated[
    UserEntity,
    Depends(require_project_administrator),
]

SprintAccessDependency = Annotated[
    UserEntity,
    Depends(require_sprint_access),
]

IssueAccessDependency = Annotated[
    UserEntity,
    Depends(require_issue_access),
]


def limit_login(request: Request) -> None:
    client_host = request.client.host if request.client else "unknown"
    rate_limiter.check(
        f"login:{client_host}",
        limit=10,
        window_seconds=60,
    )


def limit_ai_request(
    request: Request,
    user: CurrentUserDependency,
) -> None:
    rate_limiter.check(
        f"ai:{user.id}:{request.url.path}",
        limit=30,
        window_seconds=60,
    )


def limit_admin_operation(
    request: Request,
    user: CurrentUserDependency,
) -> None:
    rate_limiter.check(
        f"admin:{user.id}:{request.url.path}",
        limit=10,
        window_seconds=60,
    )


def get_rag_service(database: DatabaseSessionDependency) -> RAGService:
    """Create a project-scoped RAG service over the current database session."""
    settings = get_settings()
    return RAGService(
        session=database,
        stored_data=StoredDataService(database),
        embedding_client=OllamaEmbeddingClient(
            settings.ollama_base_url,
            settings.ollama_embedding_model,
        ),
        vector_store=PgVectorStore(database, settings.embedding_dimensions),
        answer_client=OllamaClient(
            settings.ollama_base_url,
            settings.ollama_model,
        ),
    )


RAGServiceDependency = Annotated[
    RAGService,
    Depends(get_rag_service),
]
