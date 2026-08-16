from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError

from app.api.auth_routes import router as auth_router
from app.api.routes import router
from app.core.config import (
    Settings,
    get_cors_origins_from_environment,
    get_max_request_body_bytes_from_environment,
    get_settings,
)
from app.core.logging import configure_logging
from app.core.middleware import RequestBodyLimitMiddleware, SecurityHeadersMiddleware

configure_logging()


def get_readiness_settings() -> Settings:
    """Translate invalid environment configuration into a readiness failure."""
    try:
        return get_settings()
    except ValidationError as error:
        raise HTTPException(
            status_code=503,
            detail="Application configuration is invalid.",
        ) from error


app = FastAPI(
    title="Jira AI Intelligence API",
    version="1.0",
)

cors_origins = get_cors_origins_from_environment()
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)
app.add_middleware(
    RequestBodyLimitMiddleware,
    max_bytes=get_max_request_body_bytes_from_environment(),
)
app.add_middleware(SecurityHeadersMiddleware)


app.include_router(
    auth_router,
    prefix="/api",
)

app.include_router(
    router,
    prefix="/api",
)


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    """Report process health without contacting Jira."""
    return {"status": "healthy"}


@app.get("/ready", tags=["health"])
def readiness(
    settings: Annotated[Settings, Depends(get_readiness_settings)],
) -> dict[str, str]:
    """Verify required configuration without contacting Jira."""
    return {"status": "ready"}
