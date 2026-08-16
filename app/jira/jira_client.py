import logging
from time import perf_counter
from typing import Any

import requests
from fastapi import HTTPException
from requests.auth import HTTPBasicAuth

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)
DEFAULT_PAGE_SIZE = 50


class JiraClient:
    def __init__(
        self,
        settings: Settings | None = None,
    ) -> None:
        jira_settings = settings or get_settings()
        self.base_url = str(jira_settings.jira_base_url).rstrip("/")

        self.auth = HTTPBasicAuth(
            jira_settings.jira_email,
            jira_settings.jira_api_token.get_secret_value(),
        )

        self.headers = {
            "Accept": "application/json",
        }

    def _get(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any] | list[Any]:
        url = f"{self.base_url}{endpoint}"
        started_at = perf_counter()

        try:
            response = requests.get(
                url,
                headers=self.headers,
                auth=self.auth,
                params=params,
                timeout=20,
            )

        except requests.exceptions.Timeout as error:
            logger.warning(
                "Jira request failed resource=%s category=timeout duration_ms=%.2f",
                endpoint,
                (perf_counter() - started_at) * 1000,
            )
            raise HTTPException(
                status_code=504,
                detail="The request to Jira timed out.",
            ) from error

        except requests.exceptions.ConnectionError as error:
            logger.warning(
                "Jira request failed resource=%s category=connection duration_ms=%.2f",
                endpoint,
                (perf_counter() - started_at) * 1000,
            )
            raise HTTPException(
                status_code=503,
                detail="Unable to connect to Jira.",
            ) from error

        except requests.exceptions.RequestException as error:
            logger.error(
                "Jira request failed resource=%s category=request duration_ms=%.2f",
                endpoint,
                (perf_counter() - started_at) * 1000,
            )
            raise HTTPException(
                status_code=502,
                detail="Unexpected Jira connection error.",
            ) from error

        logger.info(
            "Jira request completed resource=%s status=%s duration_ms=%.2f",
            endpoint,
            response.status_code,
            (perf_counter() - started_at) * 1000,
        )

        if response.status_code == 401:
            raise HTTPException(
                status_code=401,
                detail="Jira authentication failed.",
            )

        if response.status_code == 403:
            raise HTTPException(
                status_code=403,
                detail="You do not have permission to access this Jira resource.",
            )

        if response.status_code == 404:
            raise HTTPException(
                status_code=404,
                detail="The requested Jira resource was not found.",
            )

        if response.status_code >= 400:
            logger.error(
                "Jira request rejected resource=%s status=%s",
                endpoint,
                response.status_code,
            )
            raise HTTPException(
                status_code=response.status_code,
                detail="Jira returned an unexpected error.",
            )

        try:
            return response.json()

        except requests.exceptions.JSONDecodeError as error:
            logger.error(
                "Jira response was invalid resource=%s category=invalid_json",
                endpoint,
            )
            raise HTTPException(
                status_code=502,
                detail="Jira returned an invalid JSON response.",
            ) from error

    def _get_offset_pages(
        self,
        endpoint: str,
        item_key: str,
        params: dict[str, Any] | None = None,
        page_size: int = DEFAULT_PAGE_SIZE,
    ) -> list[Any]:
        """Collect Jira pages that use startAt/maxResults metadata."""
        items: list[Any] = []
        start_at = 0
        seen_offsets: set[int] = set()

        while start_at not in seen_offsets:
            seen_offsets.add(start_at)
            page_params = dict(params or {})
            page_params.update(
                {
                    "startAt": start_at,
                    "maxResults": page_size,
                }
            )

            data = self._get(endpoint, params=page_params)

            if not isinstance(data, dict):
                break

            page_items = data.get(item_key) or []

            if not isinstance(page_items, list) or not page_items:
                break

            items.extend(page_items)

            if data.get("isLast") is True:
                break

            total = data.get("total")

            if isinstance(total, int) and len(items) >= total:
                break

            returned_start = data.get("startAt", start_at)
            next_start = (
                returned_start + len(page_items)
                if isinstance(returned_start, int)
                else start_at + len(page_items)
            )

            if next_start <= start_at:
                break

            returned_page_size = data.get("maxResults")

            if (
                total is None
                and data.get("isLast") is None
                and isinstance(returned_page_size, int)
                and len(page_items) < returned_page_size
            ):
                break

            start_at = next_start

        return items

    def _get_array_pages(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        page_size: int = DEFAULT_PAGE_SIZE,
    ) -> list[Any]:
        """Collect Jira pages whose response is a plain JSON array."""
        items: list[Any] = []
        start_at = 0

        while True:
            page_params = dict(params or {})
            page_params.update(
                {
                    "startAt": start_at,
                    "maxResults": page_size,
                }
            )
            data = self._get(endpoint, params=page_params)

            if not isinstance(data, list) or not data:
                break

            items.extend(data)

            if len(data) < page_size:
                break

            next_start = start_at + len(data)

            if next_start <= start_at:
                break

            start_at = next_start

        return items

    def _get_token_pages(
        self,
        endpoint: str,
        item_key: str,
        params: dict[str, Any] | None = None,
        page_size: int = DEFAULT_PAGE_SIZE,
    ) -> list[Any]:
        """Collect Jira pages that use nextPageToken pagination."""
        items: list[Any] = []
        next_page_token: str | None = None
        seen_tokens: set[str] = set()

        while True:
            page_params = dict(params or {})
            page_params["maxResults"] = page_size

            if next_page_token is not None:
                page_params["nextPageToken"] = next_page_token

            data = self._get(endpoint, params=page_params)

            if not isinstance(data, dict):
                break

            page_items = data.get(item_key) or []

            if not isinstance(page_items, list):
                break

            items.extend(page_items)

            if data.get("isLast") is True:
                break

            new_token = data.get("nextPageToken")

            if not isinstance(new_token, str) or not new_token or new_token in seen_tokens:
                break

            seen_tokens.add(new_token)
            next_page_token = new_token

        return items

    @staticmethod
    def _clean_issue(
        issue: dict[str, Any],
    ) -> dict[str, Any]:
        fields = issue.get("fields") or {}

        status = fields.get("status")
        status_category = status.get("statusCategory") if status else None
        priority = fields.get("priority")
        issue_type = fields.get("issuetype")
        assignee = fields.get("assignee")
        reporter = fields.get("reporter")

        return {
            "id": issue.get("id"),
            "key": issue.get("key"),
            "summary": fields.get("summary"),
            "description": fields.get("description"),
            "status": (status.get("name") if status else None),
            "status_category": (status_category.get("name") if status_category else None),
            "priority": (priority.get("name") if priority else None),
            "issue_type": (issue_type.get("name") if issue_type else None),
            "assignee": (assignee.get("displayName") if assignee else None),
            "reporter": (reporter.get("displayName") if reporter else None),
            "created": fields.get("created"),
            "updated": fields.get("updated"),
            "resolution_date": fields.get("resolutiondate"),
            "due_date": fields.get("duedate"),
            "story_points": fields.get("customfield_10016"),
            "labels": fields.get("labels") or [],
        }

    @staticmethod
    def _issue_fields() -> str:
        return (
            "summary,"
            "description,"
            "status,"
            "priority,"
            "issuetype,"
            "assignee,"
            "reporter,"
            "created,"
            "updated,"
            "resolutiondate,"
            "duedate,"
            "customfield_10016,"
            "labels"
        )

    def get_projects(
        self,
    ) -> list[dict[str, Any]]:
        projects = self._get_offset_pages(
            "/rest/api/3/project/search",
            item_key="values",
        )

        return [
            {
                "id": project.get("id"),
                "key": project.get("key"),
                "name": project.get("name"),
            }
            for project in projects
        ]

    def get_boards(
        self,
    ) -> dict[str, Any]:
        boards = self._get_offset_pages(
            "/rest/agile/1.0/board",
            item_key="values",
        )

        return {
            "startAt": 0,
            "maxResults": len(boards),
            "total": len(boards),
            "isLast": True,
            "values": boards,
        }

    def get_board(self, board_id: int) -> dict[str, Any]:
        data = self._get(f"/rest/agile/1.0/board/{board_id}")
        if not isinstance(data, dict):
            raise HTTPException(
                status_code=502,
                detail="Jira returned an unexpected board response.",
            )
        return data

    def get_sprints(
        self,
        board_id: int,
    ) -> dict[str, Any]:
        sprints = self._get_offset_pages(
            f"/rest/agile/1.0/board/{board_id}/sprint",
            item_key="values",
        )

        return {
            "startAt": 0,
            "maxResults": len(sprints),
            "total": len(sprints),
            "isLast": True,
            "values": sprints,
        }

    def get_users(
        self,
    ) -> list[Any]:
        return self._get_array_pages(
            "/rest/api/3/users/search",
        )

    def get_issues(
        self,
        project_key: str,
    ) -> list[dict[str, Any]]:
        issues = self._get_token_pages(
            "/rest/api/3/search/jql",
            item_key="issues",
            params={
                "jql": (f"project = {self._jql_string(project_key)} ORDER BY created DESC"),
                "fields": self._issue_fields(),
            },
        )

        return [self._clean_issue(issue) for issue in issues]

    def get_updated_issues(
        self,
        project_key: str,
        updated_since: str,
    ) -> list[dict[str, Any]]:
        """Return every issue updated at or after a trusted UTC watermark."""
        issues = self._get_token_pages(
            "/rest/api/3/search/jql",
            item_key="issues",
            params={
                "jql": (
                    f"project = {self._jql_string(project_key)} "
                    f'AND updated >= "{updated_since}" '
                    "ORDER BY updated ASC"
                ),
                "fields": self._issue_fields(),
            },
        )
        return [self._clean_issue(issue) for issue in issues]

    def get_latest_updated_issue(self, project_key: str) -> dict[str, Any] | None:
        """Fetch only Jira's latest-updated issue for a lightweight freshness check."""
        data = self._get(
            "/rest/api/3/search/jql",
            params={
                "jql": (f"project = {self._jql_string(project_key)} ORDER BY updated DESC"),
                "fields": "updated",
                "maxResults": 1,
            },
        )
        if not isinstance(data, dict):
            raise HTTPException(
                status_code=502,
                detail="Jira returned an unexpected freshness response.",
            )
        issues = data.get("issues") or []
        if not isinstance(issues, list) or not issues:
            return None
        return self._clean_issue(issues[0])

    @staticmethod
    def _jql_string(value: str) -> str:
        """Quote one JQL value so it cannot terminate its string literal."""
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'

    def search_issues(
        self,
        project_key: str,
        *,
        status: str | None = None,
        assignee: str | None = None,
        priority: str | None = None,
        issue_type: str | None = None,
        label: str | None = None,
        created_from: str | None = None,
        created_to: str | None = None,
        sort_by: str = "created",
        order: str = "desc",
        limit: int = 20,
        page_token: str | None = None,
    ) -> dict[str, Any]:
        """Search one validated, cursor-paginated Jira issue page."""
        allowed_sort_fields = {"created", "updated", "duedate", "priority", "key"}
        if sort_by not in allowed_sort_fields or order not in {"asc", "desc"}:
            raise ValueError("Invalid issue sort option")

        clauses = [f"project = {self._jql_string(project_key)}"]
        filters = {
            "status": status,
            "assignee": assignee,
            "priority": priority,
            "issuetype": issue_type,
            "labels": label,
        }
        for field, value in filters.items():
            if value is not None:
                clauses.append(f"{field} = {self._jql_string(value)}")
        if created_from:
            clauses.append(f'created >= "{created_from}"')
        if created_to:
            clauses.append(f'created <= "{created_to}"')

        params: dict[str, Any] = {
            "jql": " AND ".join(clauses) + f" ORDER BY {sort_by} {order.upper()}",
            "fields": self._issue_fields(),
            "maxResults": limit,
        }
        if page_token:
            params["nextPageToken"] = page_token

        data = self._get("/rest/api/3/search/jql", params=params)
        if not isinstance(data, dict):
            raise HTTPException(
                status_code=502,
                detail="Jira returned an unexpected search response.",
            )
        raw_issues = data.get("issues") or []
        return {
            "issues": [self._clean_issue(issue) for issue in raw_issues],
            "is_last": data.get("isLast") is True,
            "next_page_token": data.get("nextPageToken"),
        }

    def get_issue(
        self,
        issue_key: str,
    ) -> dict[str, Any]:
        data = self._get(
            f"/rest/api/3/issue/{issue_key}",
            params={
                "fields": self._issue_fields(),
            },
        )

        if not isinstance(data, dict):
            raise HTTPException(
                status_code=502,
                detail="Jira returned an unexpected issue response.",
            )

        return self._clean_issue(data)

    def get_comments(
        self,
        issue_key: str,
    ) -> list[dict[str, Any]]:
        raw_comments = self._get_offset_pages(
            f"/rest/api/3/issue/{issue_key}/comment",
            item_key="comments",
            page_size=100,
        )

        comments = []

        for comment in raw_comments:
            author = comment.get("author")

            comments.append(
                {
                    "id": comment.get("id"),
                    "issue_key": issue_key,
                    "author": (author.get("displayName") if author else None),
                    "body": comment.get("body"),
                    "created": comment.get("created"),
                    "updated": comment.get("updated"),
                }
            )

        return comments

    def get_issue_changelog(
        self,
        issue_key: str,
    ) -> list[dict[str, Any]]:
        """Return every changelog history for one issue."""
        histories = self._get_offset_pages(
            f"/rest/api/3/issue/{issue_key}/changelog",
            item_key="values",
            page_size=100,
        )
        return [history for history in histories if isinstance(history, dict)]

    def get_sprint(self, sprint_id: int) -> dict[str, Any]:
        data = self._get(f"/rest/agile/1.0/sprint/{sprint_id}")
        if not isinstance(data, dict):
            raise HTTPException(
                status_code=502,
                detail="Jira returned an unexpected sprint response.",
            )
        return data

    def get_sprint_issues(
        self,
        sprint_id: int,
    ) -> list[dict[str, Any]]:
        issues = self._get_token_pages(
            f"/rest/agile/1.0/sprint/{sprint_id}/issue",
            item_key="issues",
            params={
                "fields": self._issue_fields(),
            },
        )

        return [self._clean_issue(issue) for issue in issues]
