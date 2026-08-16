# Postman and Manual Verification Guide

Despite the historical filename, this guide includes both GET and POST routes.

## Before testing

Start PostgreSQL when stored data or RAG is required:

```powershell
docker compose up -d postgres
docker compose ps
```

Activate the virtual environment:

```powershell
.\.venv\Scripts\Activate.ps1
```

Set `DATABASE_URL` to the real PostgreSQL connection in the same terminal that
will run FastAPI. Never paste the password into documentation or screenshots.

Apply migrations:

```powershell
python -m alembic upgrade head
python -m alembic current
```

Start Ollama when AI or RAG is required:

```powershell
ollama list
ollama ps
```

Start FastAPI:

```powershell
python -m uvicorn main:app
```

Base URL:

```text
http://127.0.0.1:8000
```

Swagger UI:

```text
http://127.0.0.1:8000/docs
```

## How to send JSON in Postman

1. Choose `POST`.
2. Enter the URL.
3. Open **Body**.
4. Select **raw**.
5. Select **JSON**.
6. Paste the body.
7. Click **Send**.

Postman will add `Content-Type: application/json`.

## Fast smoke test

Run these in order:

```text
GET http://127.0.0.1:8000/health
GET http://127.0.0.1:8000/ready
GET http://127.0.0.1:8000/api/
GET http://127.0.0.1:8000/api/projects
```

## Discover project, board, and sprint identifiers

Projects:

```text
GET http://127.0.0.1:8000/api/projects
```

Boards:

```text
GET http://127.0.0.1:8000/api/boards
```

Sprints for board 34:

```text
GET http://127.0.0.1:8000/api/sprints/34
```

Do not confuse a Jira display name with a project key. The verified project key
is `T1`.

## Live Jira issue checks

All T1 issues:

```text
GET http://127.0.0.1:8000/api/issues/T1
```

One issue:

```text
GET http://127.0.0.1:8000/api/issues/detail/T1-22
```

Comments for one issue:

```text
GET http://127.0.0.1:8000/api/issues/T1-22/comments
```

Issues in sprint 69:

```text
GET http://127.0.0.1:8000/api/sprints/69/issues
```

## Filtered issue search

Example first page:

```text
GET http://127.0.0.1:8000/api/issues/T1/search?status=To%20Do&assignee=noughbz&sort_by=created&order=desc&limit=2
```

Supported filters:

- `status`
- `assignee`
- `priority`
- `issue_type`
- `label`
- `created_from`
- `created_to`

Supported sorting:

- `created`
- `updated`
- `duedate`
- `priority`
- `key`

Order is `asc` or `desc`.

When `is_last` is false, copy the exact `next_page_token` value. Add it to the
next request as `page_token`. Do not decode or edit it.

## Live analytics checks

```text
GET http://127.0.0.1:8000/api/analytics/projects/T1/overview
GET http://127.0.0.1:8000/api/analytics/projects/T1/activity?stale_days=14&limit=5
GET http://127.0.0.1:8000/api/analytics/projects/T1/insights?weeks=8
GET http://127.0.0.1:8000/api/analytics/projects/T1/history?weeks=8
GET http://127.0.0.1:8000/api/analytics/projects/T1/sprints
GET http://127.0.0.1:8000/api/analytics/projects/T1/status-counts
GET http://127.0.0.1:8000/api/analytics/projects/T1/priority-counts
GET http://127.0.0.1:8000/api/analytics/projects/T1/type-counts
GET http://127.0.0.1:8000/api/analytics/projects/T1/workload
GET http://127.0.0.1:8000/api/analytics/projects/T1/overdue
GET http://127.0.0.1:8000/api/analytics/sprints/69/completion
GET http://127.0.0.1:8000/api/analytics/sprints/69/performance
```

## Synchronization checks

Full sync:

```text
POST http://127.0.0.1:8000/api/sync/projects/T1
```

No body.

Incremental sync:

```text
POST http://127.0.0.1:8000/api/sync/projects/T1/incremental
```

No body.

Recent runs:

```text
GET http://127.0.0.1:8000/api/sync/runs
```

One run:

```text
GET http://127.0.0.1:8000/api/sync/runs/5
```

A completed response should report mode, status, timestamps, project count,
issue count, sprint count, changelog count, comment count, and no error message.

## Stored-data checks

These should work without contacting Jira after a successful sync:

```text
GET http://127.0.0.1:8000/api/stored/issues/T1
GET http://127.0.0.1:8000/api/stored/analytics/projects/T1/overview
GET http://127.0.0.1:8000/api/stored/analytics/projects/T1/activity?stale_days=14&limit=5
GET http://127.0.0.1:8000/api/stored/analytics/projects/T1/insights?weeks=8
GET http://127.0.0.1:8000/api/stored/analytics/projects/T1/history?weeks=8
GET http://127.0.0.1:8000/api/stored/analytics/sprints/69/performance
```

## Deterministic delivery-risk AI

```text
POST http://127.0.0.1:8000/api/ai/projects/T1/ask
```

Body:

```json
{
  "question": "What are the main delivery risks in project T1?"
}
```

Check that risks, recommendations, and citations are consistent. A risk response
may identify the model as `deterministic-risk-engine`.

## RAG indexing

Always synchronize before indexing.

```text
POST http://127.0.0.1:8000/api/rag/projects/T1/index
```

No body.

The latest verified T1 index contained 20 chunks because the real T1 issues had
no stored descriptions or comments that produced extra chunks.

## RAG semantic search

```text
POST http://127.0.0.1:8000/api/rag/projects/T1/search
```

Body:

```json
{
  "query": "The AI invents Jira issues that do not exist",
  "top_k": 10
}
```

The expected issue `T1-22` appears in the top ten. In the verified evaluation it
ranked sixth.

## Grounded RAG answer

```text
POST http://127.0.0.1:8000/api/rag/projects/T1/ask
```

Body:

```json
{
  "question": "Which Jira issue describes the AI inventing tickets that do not exist?"
}
```

The verified response cited only `T1-22`, used `llama3.2`, considered ten chunks,
and returned `grounded: true`.

Do not use RAG to count sprints or sprint issues. Use:

```text
GET http://127.0.0.1:8000/api/analytics/projects/T1/sprints
```

If a sprint-list/count question is sent to the RAG ask route, the deterministic
question router returns this endpoint instead of calling the embedding or answer
model.

## Retrieval evaluation

Keep FastAPI running. In a second activated PowerShell terminal run:

```powershell
python -m scripts.evaluate_rag
```

Acceptance gates:

- Recall@K at least `0.8`.
- Mean Reciprocal Rank at least `0.5`.

Verified result:

- 5 hits from 5 cases.
- Recall@K `1.0`.
- Mean Reciprocal Rank `0.8333`.

## Test suite

```powershell
python -m pytest -q
```

Verified baseline:

- 84 passed.
- 3 intentionally skipped.
- 1 known non-blocking Starlette TestClient/httpx warning.

## Common error explanations

### `404 Not Found` with only `{"detail":"Not Found"}`

The running FastAPI process probably has not loaded the new route. Stop and
restart it.

### `422 Unprocessable Entity`

The path placeholder was sent literally, the JSON body is missing, or a field
name is wrong. RAG search uses `query`; RAG ask uses `question`.

### RAG `500` or `503`

Confirm PostgreSQL `DATABASE_URL`, pgvector migration, Ollama availability, and
the required local embedding model.

### PostgreSQL tests skip

Set `POSTGRES_TEST_DATABASE_URL` explicitly before opt-in PostgreSQL tests.

## Safety reminder

The FastAPI API has no application-user authentication yet. Do not expose it to
the public internet. Never include real secrets in a Postman screenshot.
