"""Tests for Jira integration."""

import pytest
import requests
from fastapi import HTTPException

from app.jira.jira_client import JiraClient


def test_clean_issue():
    raw_issue = {
        "id": "10001",
        "key": "TEST-1",
        "fields": {
            "summary": "Fix login problem",
            "description": "Users cannot sign in",
            "status": {
                "name": "In Progress",
                "statusCategory": {
                    "name": "In Progress",
                },
            },
            "priority": {
                "name": "High",
            },
            "issuetype": {
                "name": "Bug",
            },
            "assignee": {
                "displayName": "Alice",
            },
            "reporter": {
                "displayName": "Bob",
            },
            "created": "2026-07-10T09:00:00+00:00",
            "updated": "2026-07-11T10:00:00+00:00",
            "duedate": "2026-07-20",
            "labels": [
                "backend",
                "urgent",
            ],
        },
    }

    result = JiraClient._clean_issue(raw_issue)

    assert result["id"] == "10001"
    assert result["key"] == "TEST-1"
    assert result["summary"] == "Fix login problem"
    assert result["description"] == "Users cannot sign in"
    assert result["status"] == "In Progress"
    assert result["status_category"] == "In Progress"
    assert result["priority"] == "High"
    assert result["issue_type"] == "Bug"
    assert result["assignee"] == "Alice"
    assert result["reporter"] == "Bob"
    assert result["created"] == "2026-07-10T09:00:00+00:00"
    assert result["updated"] == "2026-07-11T10:00:00+00:00"
    assert result["due_date"] == "2026-07-20"
    assert result["labels"] == ["backend", "urgent"]


def test_clean_issue_handles_missing_optional_fields():
    raw_issue = {
        "id": "10002",
        "key": "TEST-2",
        "fields": {
            "summary": "Issue with missing fields",
            "description": None,
            "status": None,
            "priority": None,
            "issuetype": None,
            "assignee": None,
            "reporter": None,
            "created": None,
            "updated": None,
            "duedate": None,
            "labels": None,
        },
    }

    result = JiraClient._clean_issue(raw_issue)

    assert result["key"] == "TEST-2"
    assert result["description"] is None
    assert result["status"] is None
    assert result["priority"] is None
    assert result["issue_type"] is None
    assert result["assignee"] is None
    assert result["reporter"] is None
    assert result["due_date"] is None
    assert result["labels"] == []


def test_get_issues_quotes_project_key_as_one_jql_value(monkeypatch):
    client = JiraClient.__new__(JiraClient)
    captured = {}

    def fake_pages(path, *, item_key, params):
        captured.update(params)
        return []

    monkeypatch.setattr(client, "_get_token_pages", fake_pages)

    client.get_issues('T1" OR project = "T2')

    assert captured["jql"] == 'project = "T1\\" OR project = \\"T2" ORDER BY created DESC'


def test_get_handles_jira_timeout(monkeypatch):
    client = JiraClient.__new__(JiraClient)
    client.base_url = "https://example.atlassian.net"
    client.headers = {
        "Accept": "application/json",
    }
    client.auth = None

    def raise_timeout(*args, **kwargs):
        raise requests.exceptions.Timeout

    monkeypatch.setattr(
        requests,
        "get",
        raise_timeout,
    )

    with pytest.raises(HTTPException) as error:
        client._get("/rest/api/3/project/search")

    assert error.value.status_code == 504
    assert error.value.detail == "The request to Jira timed out."


def test_get_handles_jira_connection_error(monkeypatch):
    client = JiraClient.__new__(JiraClient)
    client.base_url = "https://example.atlassian.net"
    client.headers = {
        "Accept": "application/json",
    }
    client.auth = None

    def raise_connection_error(*args, **kwargs):
        raise requests.exceptions.ConnectionError

    monkeypatch.setattr(
        requests,
        "get",
        raise_connection_error,
    )

    with pytest.raises(HTTPException) as error:
        client._get("/rest/api/3/project/search")

    assert error.value.status_code == 503
    assert error.value.detail == "Unable to connect to Jira."


def test_get_handles_jira_authentication_failure(monkeypatch):
    client = JiraClient.__new__(JiraClient)
    client.base_url = "https://example.atlassian.net"
    client.headers = {
        "Accept": "application/json",
    }
    client.auth = None

    response = requests.Response()
    response.status_code = 401
    response.url = "https://example.atlassian.net/rest/api/3/project/search"
    response._content = b"{}"

    monkeypatch.setattr(
        requests,
        "get",
        lambda *args, **kwargs: response,
    )

    with pytest.raises(HTTPException) as error:
        client._get("/rest/api/3/project/search")

    assert error.value.status_code == 401
    assert error.value.detail == "Jira authentication failed."


def test_get_handles_jira_permission_failure(monkeypatch):
    client = JiraClient.__new__(JiraClient)
    client.base_url = "https://example.atlassian.net"
    client.headers = {
        "Accept": "application/json",
    }
    client.auth = None

    response = requests.Response()
    response.status_code = 403
    response.url = "https://example.atlassian.net/rest/api/3/project/search"
    response._content = b"{}"

    monkeypatch.setattr(
        requests,
        "get",
        lambda *args, **kwargs: response,
    )

    with pytest.raises(HTTPException) as error:
        client._get("/rest/api/3/project/search")

    assert error.value.status_code == 403
    assert error.value.detail == "You do not have permission to access this Jira resource."


def test_get_handles_missing_jira_resource(monkeypatch):
    client = JiraClient.__new__(JiraClient)
    client.base_url = "https://example.atlassian.net"
    client.headers = {
        "Accept": "application/json",
    }
    client.auth = None

    response = requests.Response()
    response.status_code = 404
    response.url = "https://example.atlassian.net/rest/api/3/issue/TEST-999"
    response._content = b"{}"

    monkeypatch.setattr(
        requests,
        "get",
        lambda *args, **kwargs: response,
    )

    with pytest.raises(HTTPException) as error:
        client._get("/rest/api/3/issue/TEST-999")

    assert error.value.status_code == 404
    assert error.value.detail == "The requested Jira resource was not found."


def test_get_handles_invalid_json(monkeypatch):
    client = JiraClient.__new__(JiraClient)
    client.base_url = "https://example.atlassian.net"
    client.headers = {
        "Accept": "application/json",
    }
    client.auth = None

    response = requests.Response()
    response.status_code = 200
    response.url = "https://example.atlassian.net/rest/api/3/project/search"
    response._content = b"This is not valid JSON"

    monkeypatch.setattr(
        requests,
        "get",
        lambda *args, **kwargs: response,
    )

    with pytest.raises(HTTPException) as error:
        client._get("/rest/api/3/project/search")

    assert error.value.status_code == 502
    assert error.value.detail == "Jira returned an invalid JSON response."


def test_get_sanitizes_unexpected_jira_error(
    monkeypatch,
    caplog,
):
    client = JiraClient.__new__(JiraClient)
    client.base_url = "https://example.atlassian.net"
    client.headers = {
        "Accept": "application/json",
    }
    client.auth = None

    response = requests.Response()
    response.status_code = 500
    response.url = "https://example.atlassian.net/rest/api/3/project/search"
    response._content = b"upstream-secret-must-not-escape"

    monkeypatch.setattr(
        requests,
        "get",
        lambda *args, **kwargs: response,
    )

    with pytest.raises(HTTPException) as error:
        client._get("/rest/api/3/project/search")

    assert error.value.status_code == 500
    assert error.value.detail == ("Jira returned an unexpected error.")
    assert "upstream-secret-must-not-escape" not in caplog.text
    assert "/rest/api/3/project/search" in caplog.text


def test_get_projects_combines_offset_pages(monkeypatch):
    client = JiraClient.__new__(JiraClient)
    requested_offsets = []

    pages = {
        0: {
            "startAt": 0,
            "maxResults": 2,
            "total": 3,
            "values": [
                {"id": "1", "key": "ONE", "name": "One"},
                {"id": "2", "key": "TWO", "name": "Two"},
            ],
        },
        2: {
            "startAt": 2,
            "maxResults": 2,
            "total": 3,
            "values": [
                {"id": "3", "key": "THREE", "name": "Three"},
            ],
        },
    }

    def fake_get(endpoint, params=None):
        assert endpoint == "/rest/api/3/project/search"
        requested_offsets.append(params["startAt"])
        return pages[params["startAt"]]

    monkeypatch.setattr(client, "_get", fake_get)

    projects = client.get_projects()

    assert requested_offsets == [0, 2]
    assert [project["key"] for project in projects] == [
        "ONE",
        "TWO",
        "THREE",
    ]


def test_get_boards_preserves_envelope_after_pagination(
    monkeypatch,
):
    client = JiraClient.__new__(JiraClient)

    pages = {
        0: {
            "startAt": 0,
            "maxResults": 1,
            "isLast": False,
            "values": [{"id": 10, "name": "Board One"}],
        },
        1: {
            "startAt": 1,
            "maxResults": 1,
            "isLast": True,
            "values": [{"id": 20, "name": "Board Two"}],
        },
    }

    monkeypatch.setattr(
        client,
        "_get",
        lambda endpoint, params=None: pages[params["startAt"]],
    )

    result = client.get_boards()

    assert result["isLast"] is True
    assert result["total"] == 2
    assert [board["id"] for board in result["values"]] == [10, 20]


def test_get_users_combines_array_pages(monkeypatch):
    client = JiraClient.__new__(JiraClient)
    requested_offsets = []

    def fake_get(endpoint, params=None):
        assert endpoint == "/rest/api/3/users/search"
        requested_offsets.append(params["startAt"])

        if params["startAt"] == 0:
            return [{"accountId": str(index)} for index in range(50)]

        return [{"accountId": "50"}]

    monkeypatch.setattr(client, "_get", fake_get)

    users = client.get_users()

    assert requested_offsets == [0, 50]
    assert len(users) == 51


def test_get_comments_combines_and_cleans_pages(monkeypatch):
    client = JiraClient.__new__(JiraClient)
    pages = {
        0: {
            "startAt": 0,
            "maxResults": 1,
            "total": 2,
            "comments": [
                {
                    "id": "1",
                    "author": {"displayName": "Alice"},
                    "body": "First",
                }
            ],
        },
        1: {
            "startAt": 1,
            "maxResults": 1,
            "total": 2,
            "comments": [
                {
                    "id": "2",
                    "author": None,
                    "body": "Second",
                }
            ],
        },
    }

    monkeypatch.setattr(
        client,
        "_get",
        lambda endpoint, params=None: pages[params["startAt"]],
    )

    comments = client.get_comments("TEST-1")

    assert [comment["id"] for comment in comments] == ["1", "2"]
    assert comments[0]["author"] == "Alice"
    assert comments[1]["author"] is None
    assert all(comment["issue_key"] == "TEST-1" for comment in comments)


def test_get_issues_combines_token_pages(monkeypatch):
    client = JiraClient.__new__(JiraClient)
    requested_tokens = []

    def issue(number):
        return {
            "id": str(number),
            "key": f"TEST-{number}",
            "fields": {
                "summary": f"Issue {number}",
            },
        }

    def fake_get(endpoint, params=None):
        assert endpoint == "/rest/api/3/search/jql"
        requested_tokens.append(params.get("nextPageToken"))

        if params.get("nextPageToken") is None:
            return {
                "isLast": False,
                "nextPageToken": "page-2",
                "issues": [issue(number) for number in range(1, 51)],
            }

        return {
            "isLast": True,
            "issues": [issue(51)],
        }

    monkeypatch.setattr(client, "_get", fake_get)

    issues = client.get_issues("TEST")

    assert requested_tokens == [None, "page-2"]
    assert len(issues) == 51
    assert issues[0]["key"] == "TEST-1"
    assert issues[-1]["key"] == "TEST-51"


def test_get_sprint_issues_uses_agile_token_endpoint(
    monkeypatch,
):
    client = JiraClient.__new__(JiraClient)
    requested_endpoints = []

    def fake_get(endpoint, params=None):
        requested_endpoints.append(endpoint)

        if params.get("nextPageToken") is None:
            return {
                "isLast": False,
                "nextPageToken": "sprint-page-2",
                "issues": [
                    {
                        "id": "1",
                        "key": "TEST-1",
                        "fields": {"summary": "First"},
                    }
                ],
            }

        return {
            "isLast": True,
            "issues": [
                {
                    "id": "2",
                    "key": "TEST-2",
                    "fields": {"summary": "Second"},
                }
            ],
        }

    monkeypatch.setattr(client, "_get", fake_get)

    issues = client.get_sprint_issues(42)

    assert requested_endpoints == [
        "/rest/agile/1.0/sprint/42/issue",
        "/rest/agile/1.0/sprint/42/issue",
    ]
    assert [issue["key"] for issue in issues] == [
        "TEST-1",
        "TEST-2",
    ]


def test_get_issue_changelog_combines_pages(monkeypatch):
    client = JiraClient.__new__(JiraClient)
    pages = [
        {"startAt": 0, "maxResults": 1, "total": 2, "values": [{"id": "1", "items": []}]},
        {"startAt": 1, "maxResults": 1, "total": 2, "values": [{"id": "2", "items": []}]},
    ]

    monkeypatch.setattr(client, "_get", lambda *args, **kwargs: pages.pop(0))

    result = client.get_issue_changelog("TEST-1")

    assert [history["id"] for history in result] == ["1", "2"]


def test_search_issues_builds_safe_jql_and_forwards_cursor(monkeypatch):
    client = JiraClient.__new__(JiraClient)
    captured = {}

    def fake_get(endpoint, params=None):
        captured["endpoint"] = endpoint
        captured["params"] = params
        return {
            "issues": [
                {
                    "id": "1",
                    "key": "TEST-1",
                    "fields": {"summary": "Safe result"},
                }
            ],
            "isLast": False,
            "nextPageToken": "next-token",
        }

    monkeypatch.setattr(client, "_get", fake_get)
    result = client.search_issues(
        "T1",
        status='To Do" OR project = "OTHER',
        assignee="Alice",
        created_from="2026-07-01",
        created_to="2026-07-12",
        sort_by="updated",
        order="asc",
        limit=10,
        page_token="current-token",
    )

    assert captured["endpoint"] == "/rest/api/3/search/jql"
    jql = captured["params"]["jql"]
    assert 'project = "T1"' in jql
    assert 'status = "To Do\\" OR project = \\"OTHER"' in jql
    assert 'assignee = "Alice"' in jql
    assert 'created >= "2026-07-01"' in jql
    assert 'created <= "2026-07-12"' in jql
    assert jql.endswith("ORDER BY updated ASC")
    assert captured["params"]["maxResults"] == 10
    assert captured["params"]["nextPageToken"] == "current-token"
    assert result["next_page_token"] == "next-token"
    assert result["issues"][0]["key"] == "TEST-1"


def test_search_issues_rejects_non_allowlisted_sort():
    client = JiraClient.__new__(JiraClient)

    with pytest.raises(ValueError):
        client.search_issues("TEST", sort_by="created DESC OR key")


def test_get_updated_issues_uses_trusted_watermark(monkeypatch):
    client = JiraClient.__new__(JiraClient)
    captured = {}

    def fake_pages(endpoint, item_key, params=None, page_size=50):
        captured.update(params)
        return []

    monkeypatch.setattr(client, "_get_token_pages", fake_pages)

    assert client.get_updated_issues("T1", "2026-07-12 22:05") == []
    assert captured["jql"] == (
        'project = "T1" AND updated >= "2026-07-12 22:05" ORDER BY updated ASC'
    )


def test_get_latest_updated_issue_requests_only_one_candidate(monkeypatch):
    client = JiraClient.__new__(JiraClient)
    captured = {}

    def fake_get(endpoint, params=None):
        captured["endpoint"] = endpoint
        captured["params"] = params
        return {
            "issues": [
                {
                    "id": "10001",
                    "key": "T1-1",
                    "fields": {"updated": "2026-08-05T10:30:00+00:00"},
                }
            ]
        }

    monkeypatch.setattr(client, "_get", fake_get)

    result = client.get_latest_updated_issue('T1" OR project = "T2')

    assert result["key"] == "T1-1"
    assert captured["endpoint"] == "/rest/api/3/search/jql"
    assert captured["params"]["maxResults"] == 1
    assert captured["params"]["fields"] == "updated"
    assert captured["params"]["jql"] == (
        'project = "T1\\" OR project = \\"T2" ORDER BY updated DESC'
    )
