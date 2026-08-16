"""Tests for typed application configuration."""

import pytest
from pydantic import ValidationError

from app.core.config import Settings, parse_allowed_cors_origins
from app.jira.jira_client import JiraClient


def test_settings_accept_safe_explicit_values():
    settings = Settings(
        _env_file=None,
        jira_base_url="https://example.atlassian.net",
        jira_email="developer@example.com",
        jira_api_token="test-token-not-a-real-secret",
        jwt_secret_key="test-jwt-secret-key-with-at-least-32-characters",
    )

    assert str(settings.jira_base_url) == ("https://example.atlassian.net/")
    assert settings.jira_email == "developer@example.com"
    assert "test-token-not-a-real-secret" not in repr(settings)
    assert settings.max_request_body_bytes == 1_048_576


def test_settings_require_all_jira_values(monkeypatch):
    for variable in (
        "JIRA_BASE_URL",
        "JIRA_EMAIL",
        "JIRA_API_TOKEN",
    ):
        monkeypatch.delenv(variable, raising=False)

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_jira_client_uses_injected_settings():
    settings = Settings(
        _env_file=None,
        jira_base_url="https://example.atlassian.net/",
        jira_email="developer@example.com",
        jira_api_token="test-token-not-a-real-secret",
        jwt_secret_key="test-jwt-secret-key-with-at-least-32-characters",
    )

    client = JiraClient(settings=settings)

    assert client.base_url == "https://example.atlassian.net"
    assert client.auth.username == "developer@example.com"
    assert client.auth.password == "test-token-not-a-real-secret"
    assert not hasattr(client, "api_token")


def test_cors_configuration_normalizes_origins_and_rejects_wildcard():
    assert parse_allowed_cors_origins(" http://localhost:3000/, https://dashboard.example/ ") == [
        "http://localhost:3000",
        "https://dashboard.example",
    ]

    with pytest.raises(ValueError, match="cannot contain"):
        parse_allowed_cors_origins("*")


def test_request_body_limit_rejects_unsafe_configuration():
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            jira_base_url="https://example.atlassian.net",
            jira_email="developer@example.com",
            jira_api_token="test-token-not-a-real-secret",
            jwt_secret_key="test-jwt-secret-key-with-at-least-32-characters",
            max_request_body_bytes=1023,
        )
