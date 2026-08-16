# API Documentation

## Authentication

Health and readiness endpoints remain public. Business endpoints require:

```http
Authorization: Bearer <access-token>
```

Create prototype users interactively after applying the latest migration:

```powershell
python -m scripts.create_user viewer-demo --role viewer --first-name Nour --last-name Viewer --email nour.viewer@example.com
python -m scripts.create_user admin-demo --role admin --first-name Nour --last-name Admin --email nour.admin@example.com
```

Passwords are prompted securely and are not command-line arguments. Running the
same command for an existing username updates its password, role, and any
profile fields supplied. First name, last name, and email are optional so users
created by earlier migrations continue to work.

### Login

```http
POST /api/auth/login
Content-Type: application/json
```

```json
{
  "username": "viewer-demo",
  "password": "your-password"
}
```

The response contains `access_token`, bearer `token_type`, and
`expires_in_seconds`. `GET /api/auth/me` returns the internal username and role
plus optional first name, last name, and email. The dashboard displays `viewer`
as the user-friendly label **Team Member**; the internal value remains stable
for authorization compatibility.

### Current identity

```http
GET /api/auth/me
Authorization: Bearer <access-token>
```

Viewers can read Jira and stored data and use analytics, AI, and RAG question
routes. Administrators have the same access and can additionally call:

- `POST /api/sync/projects/{project_key}`
- `POST /api/sync/projects/{project_key}/incremental`
- `POST /api/rag/projects/{project_key}/index`

## Base URLs

Application root:

```text
http://127.0.0.1:8000
```

API prefix:

```text
http://127.0.0.1:8000/api
```

Interactive documentation:

```text
http://127.0.0.1:8000/docs
```

### Shared synchronization freshness

```http
GET /api/sync/projects/{project_key}/freshness
Authorization: Bearer <viewer-or-admin-token>
```

This response contains the latest completed sync marker plus the cached Jira
freshness result. Team Member dashboards poll it every 15 seconds. Jira itself is
queried at most once per project per 60 seconds. A newer Jira issue produces
`sync_required: true` and **Updates available — sync required**. When the completed
sync ID changes, cached project queries refresh automatically.

### Deterministic structured Jira questions

`POST /api/rag/projects/{project_key}/ask` detects questions that filter issues
by priority, status, assignee, or issue type. It reads the synchronized issue
columns directly and responds with model `deterministic-issue-field-filter`,
exact matching issue keys, and `retrieved_chunks: 0`. This path does not call
Ollama or pgvector. Small spelling errors are tolerated; an unclear or absent
value returns the available project values for clarification.

## Common behavior

- Request and response bodies use JSON.
- Invalid Pydantic input normally returns `422`.
- A POST, PUT, or PATCH body larger than `MAX_REQUEST_BODY_BYTES` returns `413`
  before route or authentication processing.
- Missing project or sprint evidence normally returns `404`.
- Jira or Ollama failures are sanitized.
- Project keys accepted by protected path validators begin with a letter and may
  contain letters, numbers, underscores, or hyphens.
- Swagger UI is the authoritative runtime view of the current schema.
- Protected API responses use `Cache-Control: no-store` and defensive browser
  headers. See [security.md](security.md) for their purpose and limitations.

## Health routes

### Process health

```text
GET /health
```

Returns `{"status":"healthy"}` without contacting Jira.

### Configuration readiness

```text
GET /ready
```

Validates application settings without contacting Jira.

## API root

```text
GET /api/
```

Returns a simple running message.

## Live Jira routes

These routes contact Jira Cloud.

### Projects

```text
GET /api/projects
```

### Boards

```text
GET /api/boards
```

### Sprints for a board

```text
GET /api/sprints/{board_id}
```

### Issues for a sprint

```text
GET /api/sprints/{sprint_id}/issues
```

### Visible Jira users

```text
GET /api/users
```

### Project issues

```text
GET /api/issues/{project_key}
```

### One issue

```text
GET /api/issues/detail/{issue_key}
```

### Issue comments

```text
GET /api/issues/{issue_key}/comments
```

### Safe issue search

```text
GET /api/issues/{project_key}/search
```

Optional parameters:

- `status`
- `assignee`
- `priority`
- `issue_type`
- `label`
- `created_from`
- `created_to`
- `sort_by`: `created`, `updated`, `duedate`, `priority`, or `key`
- `order`: `asc` or `desc`
- `limit`
- `page_token`

Example:

```text
GET /api/issues/T1/search?status=To%20Do&assignee=noughbz&sort_by=created&order=desc&limit=20
```

When `is_last` is false, copy `next_page_token` into the next request's
`page_token` parameter.

## Live analytics routes

These deprecated diagnostic routes retrieve current data from Jira and then
calculate metrics. They remain available for integration troubleshooting and
backward compatibility, but product screens must use the stored-data routes.
This avoids repeated Jira calls and keeps every user on the same synchronized
snapshot.

### Project overview

```text
GET /api/analytics/projects/{project_key}/overview
```

### Project activity

```text
GET /api/analytics/projects/{project_key}/activity?stale_days=14&limit=5
```

### Project insights

```text
GET /api/analytics/projects/{project_key}/insights?weeks=8
```

### Project history

```text
GET /api/analytics/projects/{project_key}/history?weeks=8
```

### Project sprint summary

```text
GET /api/analytics/projects/{project_key}/sprints
```

Returns every discovered sprint for the project's Jira boards with its name,
state, board ID, dates, issue count, completed count, open count, and completion
rate. This is the authoritative endpoint for sprint-list and sprint-count
questions.

### Status counts

```text
GET /api/analytics/projects/{project_key}/status-counts
```

### Priority counts

```text
GET /api/analytics/projects/{project_key}/priority-counts
```

### Issue-type counts

```text
GET /api/analytics/projects/{project_key}/type-counts
```

### Workload

```text
GET /api/analytics/projects/{project_key}/workload
```

### Overdue issues

```text
GET /api/analytics/projects/{project_key}/overdue
```

### Sprint completion

```text
GET /api/analytics/sprints/{sprint_id}/completion
```

### Sprint performance

```text
GET /api/analytics/sprints/{sprint_id}/performance
```

## Synchronization routes

### Full project synchronization

```text
POST /api/sync/projects/{project_key}
```

No body is required. The response includes project, issue, sprint, changelog, and
comment counts.

### Incremental project synchronization

```text
POST /api/sync/projects/{project_key}/incremental
```

No body is required. Without a successful baseline, it falls back to full sync.

### Force a Jira update check

```text
POST /api/sync/projects/{project_key}/check
```

Requires company or project administration. It bypasses the one-minute shared
cache and compares Jira's latest-updated issue with the stored issue timestamp.

### Recent synchronization runs

```text
GET /api/sync/runs?limit=20
```

### One synchronization run

```text
GET /api/sync/runs/{run_id}
```

The detailed response includes an issue-level `changes` array for runs created
after migration `20260805_08`. Each item contains its created/updated/unchanged
classification, changed fields, before/after values, and inspected history and
comment counts.

## Stored-data routes

These routes read PostgreSQL or SQLite and do not contact Jira.

### Stored issues

```text
GET /api/stored/issues/{project_key}
```

### Stored sprint portfolio

```text
GET /api/stored/analytics/projects/{project_key}/sprints
```

Returns the synchronized active, future, and completed sprints with authoritative
membership and completion counts. It does not contact Jira during the request.

### Stored sprint issues

```text
GET /api/stored/sprints/{sprint_id}/issues
```

Returns the synchronized membership snapshot. A known sprint with no issues
returns an empty list; an unknown or unauthorized sprint does not expose data.

### Stored overview

```text
GET /api/stored/analytics/projects/{project_key}/overview
```

### Stored activity

```text
GET /api/stored/analytics/projects/{project_key}/activity?stale_days=14&limit=5
```

### Stored insights

```text
GET /api/stored/analytics/projects/{project_key}/insights?weeks=8
```

### Stored history

```text
GET /api/stored/analytics/projects/{project_key}/history?weeks=8
```

### Canonical delivery risks

```text
GET /api/stored/analytics/projects/{project_key}/risks
```

Returns the active blocked, overdue, stale, unassigned, workload-concentration,
and low-completion signals from the shared deterministic risk engine. Risk
Center and the AI risk API use these same rules and thresholds.

### Stored sprint performance

```text
GET /api/stored/analytics/sprints/{sprint_id}/performance
```

## Grounded AI route

```text
POST /api/ai/projects/{project_key}/ask
Content-Type: application/json
```

Body:

```json
{
  "question": "What are the main delivery risks?"
}
```

Risk questions use deterministic risk signals and recommendations. Non-risk
questions may use local `llama3.2` with project evidence. The response includes
answer text, risks, recommendations, source issue keys, limitations, model name,
and `grounded`.

The dashboard presents Risk Center as the single user-facing risk workflow. This
endpoint remains useful for API integrations and uses the same shared rule
engine; it is not a second independent risk calculation.

## RAG routes

RAG routes require PostgreSQL with pgvector and a running Ollama service.

### Index project knowledge

```text
POST /api/rag/projects/{project_key}/index
```

No body is required. It indexes synchronized summaries, descriptions, and
comments.

### Semantic search

```text
POST /api/rag/projects/{project_key}/search
Content-Type: application/json
```

Body:

```json
{
  "query": "The AI invents Jira issues that do not exist",
  "top_k": 10
}
```

`query` must contain 3 to 1000 characters. `top_k` must be between 1 and 20.

### Grounded RAG answer

```text
POST /api/rag/projects/{project_key}/ask
Content-Type: application/json
```

Body:

```json
{
  "question": "Which Jira issue describes the AI inventing tickets?"
}
```

The service retrieves ten project-scoped chunks, asks local `llama3.2`, removes
unsupported citations, and returns an insufficient-evidence answer when no real
retrieved issue supports the result.

Structured sprint-list and issue-count questions are deliberately refused before
retrieval. The response directs the caller to
`GET /api/analytics/projects/{project_key}/sprints` because RAG chunks are not an
authoritative source of sprint membership counts.

## Dashboard-support endpoints

### Safe Jira client configuration

```text
GET /api/client-config
Authorization: Bearer <viewer-or-admin-token>
```

Returns only the configured Jira base URL so the dashboard can create links such
as `https://company.atlassian.net/browse/T1-22`. It never returns the Jira email,
API token, database URL, or model configuration.

Example response:

```json
{
  "jira_base_url": "https://company.atlassian.net"
}
```

### RAG index status

```text
GET /api/rag/projects/{project_key}/status
Authorization: Bearer <viewer-or-admin-token>
```

Reads PostgreSQL metadata without calling Jira or Ollama. The dashboard uses it
to explain whether project knowledge is indexed and how fresh it is.

Example response:

```json
{
  "project_key": "T1",
  "issues_indexed": 20,
  "chunks_indexed": 20,
  "last_indexed_at": "2026-07-14T15:55:00Z",
  "latest_source_update": "2026-07-14T15:52:02Z"
}
```

The existing `GET /api/sync/runs?limit=20` endpoint supplies synchronization
freshness and audit history. Synchronization and index rebuild endpoints remain
administrator-only even though viewers may read their status.

## Important distinctions

- `/api/analytics/...` contacts Jira.
- `/api/stored/analytics/...` uses synchronized database data.
- `/api/ai/.../ask` uses structured project evidence and deterministic risks.
- `/api/rag/.../search` exposes raw semantic candidates.
- `/api/rag/.../ask` retrieves candidates and produces a grounded explanation.

## Verified examples

Current development identifiers:

- Project key: `T1`
- Board ID: `34`
- Sprint IDs used during verification: `34`, `68`, and `69`

These are development examples, not hardcoded application requirements.

## Current limitations

- Local JWT identities are a prototype substitute for company SSO/OIDC.
- Authorization is role-based and project-specific within one modeled company;
  multi-company tenancy is not implemented.
- Rate limiting is process-local rather than shared across server workers.
- No scheduled synchronization.
- No public production deployment.
- Knowledge-answer quality depends on the content available in each synchronized
  project's Jira summaries, descriptions, and comments.

For step-by-step Postman instructions, see
[postman-get-routes.md](postman-get-routes.md).
