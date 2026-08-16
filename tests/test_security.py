"""Transport-layer security regression tests."""

import asyncio
import json

from fastapi.testclient import TestClient

from app.core.middleware import RequestBodyLimitMiddleware
from main import app


def test_api_responses_are_not_cached_and_include_security_headers():
    response = TestClient(app).get("/api/projects")

    assert response.status_code == 401
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["cross-origin-resource-policy"] == "same-origin"
    assert "camera=()" in response.headers["permissions-policy"]
    assert "default-src 'none'" in response.headers["content-security-policy"]
    assert "strict-transport-security" not in response.headers


def test_oversized_login_body_is_rejected_before_authentication():
    response = TestClient(app).post(
        "/api/auth/login",
        content=b"x" * 1_048_577,
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 413
    assert response.json() == {"detail": "Request body is too large."}
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-content-type-options"] == "nosniff"


def test_body_limit_measures_chunked_content_without_content_length():
    downstream_called = False
    sent = []
    incoming = iter(
        [
            {"type": "http.request", "body": b"1234", "more_body": True},
            {"type": "http.request", "body": b"5678", "more_body": False},
        ]
    )

    async def downstream(scope, receive, send):
        nonlocal downstream_called
        downstream_called = True

    async def receive():
        return next(incoming)

    async def send(message):
        sent.append(message)

    middleware = RequestBodyLimitMiddleware(downstream, max_bytes=7)
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/auth/login",
        "headers": [],
    }
    asyncio.run(middleware(scope, receive, send))

    assert downstream_called is False
    assert sent[0]["status"] == 413
    assert json.loads(sent[1]["body"]) == {"detail": "Request body is too large."}
