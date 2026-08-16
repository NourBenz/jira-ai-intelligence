# Jira AI Intelligence — Keep-Up and Project Defense Guide

This document is the study guide for explaining the completed prototype through
Phase 12 and the project-authorization hardening batch. Read it before a supervisor review, technical interview, demonstration,
or internship presentation.

It focuses on four questions:

- What did we build?
- Why did we build it this way?
- How does it work internally?
- What should I say when someone challenges a technical decision?

Do not memorize every sentence. Understand the flow and explain it in your own
words.

## The simplest explanation of the project

Jira AI Intelligence is a backend system that connects to Jira Cloud, collects
project and sprint data, calculates reliable delivery metrics, stores historical
data, and uses a local AI and RAG pipeline to answer questions using real Jira
evidence.

The system is designed to help a software team understand questions such as:

- How much work is complete?
- Who owns the open work?
- Which tasks are overdue, stale, blocked, or unassigned?
- What changed during a sprint?
- What is the sprint throughput, velocity, cycle time, or lead time?
- Which Jira ticket describes a problem written in different words?
- What evidence supports an AI answer?

The system does not replace Jira. Jira remains the source where the team manages
issues, boards, sprints, comments, and workflows. This project adds a controlled
analytics, persistence, and AI intelligence layer on top of Jira.

## How company, team, and project access works

The prototype represents one company with multiple Scrum teams. Each Jira project
has one owning team, but a team can own several projects and a person can belong
to several teams. A Team Member sees only projects owned by their active teams.

There are two administrative scopes:

- A company administrator manages every project, team, membership, and access
  assignment.
- A project administrator can synchronize Jira data and rebuild the RAG index
  only for explicitly assigned projects.

Developer, QA, Product Owner, and Scrum Master are useful Scrum responsibilities,
but they are not automatically security roles. The company deliberately assigns
administrative authority rather than assuming that every Product Owner or Scrum
Master must receive it.

The dashboard project selector is therefore an authorization result, not a key
entry mechanism. Knowing another project's Jira key does not grant access. The
backend checks the parent project even when a request starts from a sprint ID or
issue key, preventing indirect cross-team reads.

Synchronization is observable rather than a blind refresh. The system checks
Jira's most recently updated issue against the stored snapshot and warns when a
sync is required. Every new sync records which issue snapshots were created,
updated, or unchanged and which fields differed. Open dashboards still poll the
shared completed-sync marker and refresh automatically after an administrator
finishes synchronization.

## A strong 30-second project pitch

> I built a FastAPI backend that integrates with Jira Cloud, safely synchronizes
> project data into PostgreSQL, calculates deterministic engineering metrics, and
> provides grounded AI answers. Reliable facts such as completion rates and
> delivery risks are calculated in code. Semantic questions use a local RAG
> pipeline with Ollama, `nomic-embed-text`, and pgvector. Every answer is limited
> to synchronized project evidence and citations are checked against real Jira
> issue keys.

## What problem the project solves

Jira stores useful operational data, but teams still face several problems:

- Information is spread across issues, sprints, status changes, comments, and
  fields.
- Managers may need combined metrics that are not available in one API response.
- Repeatedly calling Jira for every dashboard calculation is slow and fragile.
- Natural-language questions may describe the same problem with different words.
- A normal language model can invent issues, people, recommendations, or numbers.
- Cloud AI can create privacy, cost, and API-key concerns.

The prototype addresses these problems by separating the system into reliable
layers:

1. Jira integration retrieves authoritative source data.
2. Synchronization stores a consistent local snapshot and history.
3. Deterministic analytics calculates facts.
4. The evidence layer prepares safe, project-scoped facts for AI.
5. RAG retrieves relevant unstructured Jira text.
6. A local language model explains retrieved evidence.

## The architecture in plain language

The normal live-data path is:

```text
Postman or future dashboard
        -> FastAPI route
        -> JiraService
        -> JiraClient
        -> Jira Cloud REST API
        -> cleaned Ticket models
        -> AnalyticsService
        -> validated JSON response
```

The stored-data path is:

```text
Jira Cloud
        -> full or incremental synchronization
        -> SQLAlchemy repositories
        -> PostgreSQL
        -> StoredDataService
        -> analytics or AI evidence
        -> API response
```

The RAG path is:

```text
Stored Jira summaries, descriptions, and comments
        -> deterministic chunks with Jira metadata
        -> nomic-embed-text document embeddings
        -> PostgreSQL pgvector

User question
        -> nomic-embed-text query embedding
        -> project-filtered cosine search
        -> top 10 Jira chunks
        -> local llama3.2 grounded answer
        -> citation validation
        -> final answer with real Jira keys
```

## The main technologies and why they exist

### Python 3.12

Python is used because it has mature libraries for APIs, data validation,
databases, testing, and AI integration. Version 3.12 gives modern typing and good
runtime support.

### FastAPI

FastAPI exposes the backend as HTTP endpoints. It was selected because it
supports:

- Type-based request validation.
- Automatic OpenAPI and Swagger documentation at `/docs`.
- Dependency injection for testability.
- Pydantic response models.
- Clear HTTP error handling.

FastAPI routes should remain thin. A route validates HTTP input, calls a service,
and returns a response. Business logic belongs in services.

### Pydantic and pydantic-settings

Pydantic validates request bodies and response structures. The Settings model
validates required configuration such as Jira credentials, database URL, Ollama
URL, model names, and embedding dimensions.

Why this matters: invalid configuration fails in a predictable way instead of
causing confusing errors later.

### Requests

The Requests library performs HTTP calls to Jira and Ollama. The clients convert
timeouts, connection failures, authentication errors, permission errors, missing
resources, and malformed responses into sanitized API errors.

### SQLAlchemy

SQLAlchemy maps Python entities to relational database tables. It separates
application code from database-specific SQL and supports both SQLite and
PostgreSQL.

### Alembic

Alembic versions the database schema. Each migration represents a controlled
schema change. This is safer and repeatable compared with manually editing a
database.

Current important revisions include:

- Initial persistence tables.
- Sprint-to-issue membership storage.
- pgvector RAG storage.
- Jira comment persistence and synchronization counts.
- Prototype application users and roles.

The verified current PostgreSQL head is `20260723_05`.

### PostgreSQL

PostgreSQL is the production-like database for the prototype. It stores projects,
issues, sprints, sprint memberships, changelogs, comments, synchronization runs,
RAG chunks, and prototype user identities.

SQLite is still useful for lightweight development and isolated automated tests.
RAG vector storage intentionally requires PostgreSQL with pgvector.

### Docker Compose

Docker Compose starts a reproducible PostgreSQL 17 service with pgvector. A named
volume preserves data when the container restarts. Credentials remain in an
ignored environment file and are not committed.

### Ollama

Ollama runs AI models locally. This avoids a paid cloud API and keeps synchronized
Jira evidence on the developer machine.

The selected models are:

- `llama3.2` for answer generation.
- `nomic-embed-text` for embeddings.

`qwen3:8b` was downloaded and tested, but a CUDA initialization failure made it
unsuitable for the current machine during Phase 6. The architecture keeps the
model client separate, so the answer model can be changed later without rewriting
the whole application.

### pgvector

pgvector adds vector columns and similarity search to PostgreSQL. Each Jira text
chunk stores a 768-dimensional embedding. A question embedding is compared with
stored embeddings using cosine distance.

### pytest

pytest verifies behavior offline. Tests use fake Jira data, fake model responses,
dependency overrides, and monkeypatching. They do not modify the real Jira
project unless an explicit live test is performed manually.

The latest verified suite result is:

- 110 tests passed.
- 0 tests skipped when PostgreSQL integration tests are enabled.
- 83.56% combined statement and branch coverage.
- 1 non-blocking Starlette TestClient/httpx deprecation warning.

## Why fake data in tests is valuable

Fake data is not intended to replace real Jira verification. It gives us
controlled and repeatable situations that may be difficult or dangerous to
create in the company project.

Examples include:

- A Jira timeout.
- Invalid JSON from an upstream service.
- More than 50 issues requiring pagination.
- A missing optional field.
- A malicious or invented citation.
- An issue changing sprint after sprint start.
- A comment being updated or deleted.

Offline tests are fast and safe. Live tests confirm that the real integration
works. A professional prototype needs both.

## Phase 1 — Backend stabilization and Jira integration

### What was built

- A working FastAPI application entry point.
- Typed configuration loaded from environment variables.
- Safe `.env.example` documentation.
- Jira projects, boards, sprints, users, issues, comments, and changelog access.
- Cleaning of raw Jira JSON into consistent Ticket models.
- Endpoint-specific pagination for multiple Jira API formats.
- Safe logging and sanitized error responses.
- Dependency injection for JiraService.
- `/health` and `/ready` endpoints.
- Status-category-based completion detection.
- Meaningful offline tests replacing placeholders.

### Why raw Jira responses are cleaned

Jira responses are deeply nested and optional fields may be `null`. Application
code should not repeatedly understand Jira's raw structure.

The Jira client converts fields into a stable internal Ticket model containing
values such as:

- Key and summary.
- Description.
- Status and status category.
- Priority and issue type.
- Assignee and reporter.
- Creation, update, resolution, and due dates.
- Story points and labels.

This creates a boundary between the external Jira API and internal logic.

### Why status category is used for completion

Different companies use different status names. One project may use `Done`,
another may use `Released` or `Accepted`. Jira's status category provides the
more reliable workflow meaning.

The system considers an issue complete when its status category is `Done`. It
uses a small fallback list only when the category is missing.

### Why pagination was complicated

Jira endpoints do not all paginate in the same way:

- Some use offset fields such as `startAt` and `maxResults`.
- Some return arrays.
- New search endpoints may use `nextPageToken`.
- Agile endpoints have their own response envelopes.

The client uses endpoint-specific pagination so large projects are not silently
truncated at 50 issues.

### Why dependency injection matters

Routes receive JiraService through FastAPI dependencies. Tests can replace the
real service with a fake implementation. This proves route behavior without
credentials, network calls, or Jira modifications.

### What `/health` and `/ready` mean

- `/health` confirms that the process is running.
- `/ready` validates that required configuration can be loaded.

Neither endpoint should make a Jira request. Monitoring must remain cheap and
must not fail merely because Jira is temporarily slow.

## Phase 2 — Deterministic analytics

### Why the analytics are deterministic

A completion percentage must always be mathematically correct. It should not
depend on language-model interpretation. Therefore counts, dates, workload,
velocity, and risk signals are calculated in normal Python code.

The AnalyticsService is pure: it receives already-fetched Ticket objects and
does not call Jira or the database.

### Current-state metrics

The project can calculate:

- Total, open, and completed issue counts.
- Completion rate.
- Status, priority, and issue-type distributions.
- Workload by assignee.
- Unassigned work.
- Overdue work.
- Average issue age.
- Oldest open issues.
- Recently updated and stale issues.
- Label counts.
- Workload matrices by status and priority.
- A basic blocked-work signal.

### The blocked-work rule

An open issue is considered blocked when its status or one of its labels contains
the word `block`, case-insensitively.

This rule is deliberately documented as a basic signal. A future organization
could configure more advanced rules.

### Historical metrics

Historical calculations use Jira changelogs and timestamps:

- Completed issues per week.
- Lead time.
- Cycle time.
- Sprint throughput.
- Completed and committed story points when available.
- Sprint scope additions and removals.
- Sprint carryover.

### Lead time versus cycle time

- Lead time measures from issue creation until resolution.
- Cycle time measures from the first transition into active work until
  resolution.

Lead time includes waiting before work begins. Cycle time focuses on execution.

### Velocity versus throughput

- Throughput is the number of completed issues.
- Velocity is completed story points when story points exist.

The prototype does not invent story points. If Jira lacks estimates, point-based
metrics return no value while issue-count throughput remains available.

### Sprint scope change and carryover

The system reads sprint-field changelog entries:

- Added after sprint start means scope was added.
- Removed after sprint start means scope was removed.
- An issue added from an earlier sprint can indicate carryover.

These metrics require history. Current issue state alone cannot explain when the
scope changed.

## Phase 3 — Safe filtering, sorting, and search

### What was built

The search endpoint supports validated filters for:

- Status.
- Assignee.
- Priority.
- Issue type.
- Label.
- Creation date range.
- Allowlisted sort field and direction.
- Bounded result limit.
- Jira cursor continuation token.

### Why not accept raw JQL from the user

Direct raw JQL would allow invalid or injection-like input and would expose Jira
query behavior unnecessarily.

The application builds JQL only from allowlisted fields and escaped values.
Invalid sort options and reversed date ranges are rejected before Jira is
contacted.

### How cursor pagination works

The first response returns a `next_page_token` when more data exists. The client
sends that opaque token in the next request. The token is not interpreted or
manually edited by the application user.

## Phase 4 — Persistence and synchronization

### Why a database was added

Without persistence, every analytics or AI question would call Jira repeatedly.
That would increase latency, consume API capacity, and make historical analysis
harder.

The database provides:

- A synchronized snapshot.
- Historical changelogs.
- Sprint membership.
- Comment evidence.
- Fast network-free analytics reads.
- A foundation for RAG indexing.
- Auditable synchronization runs.

### Main database entities

- Project: Jira project identity and synchronization time.
- Issue: normalized issue fields.
- Sprint: sprint dates, state, goal, and board.
- Sprint issue: relational membership between a sprint and an issue.
- Changelog: Jira history entries used for status and sprint analysis.
- Comment: Jira comment content, author, ID, and timestamps.
- Sync run: mode, status, timestamps, counts, and safe error message.
- RAG chunk: source text, metadata, content hash, and vector embedding.

### Full synchronization

A full sync retrieves the selected project, all issues, each issue's changelog
and comments, matching project sprints, and sprint memberships.

It upserts existing records instead of blindly inserting duplicates. Comment
snapshots are replaced per issue so deleted Jira comments do not remain locally.

### Incremental synchronization

Incremental sync uses the most recent successful completion time as a UTC minute
watermark and asks Jira only for updated issues. It then refreshes those issues,
their history, comments, and current sprint information.

If there is no successful baseline, it safely falls back to a full sync.

### What idempotent means

Idempotent means repeating the same synchronization produces the same logical
database state rather than duplicate projects, issues, histories, comments, or
sprint links.

### Why caching was deferred

Database-backed reads were already fast. Adding a cache without a measured
bottleneck would introduce invalidation complexity. The decision to defer caching
is an engineering decision based on evidence, not missing ambition.

### Live Phase 4 and Phase 6 storage evidence

The final verified T1 full synchronization processed:

- 20 issues.
- 3 sprints.
- 80 changelog records.
- 0 comments in the current real T1 dataset.

Zero comments is not an error. Automated tests verify non-empty comment storage
and chunking.

## Phase 5 — Grounded AI assistant

### Why a normal chatbot was not enough

A normal LLM can produce convincing but unsupported answers. For a company tool,
invented issues or recommendations are unacceptable.

The assistant therefore receives a controlled evidence package built from the
synchronized database.

### Deterministic facts versus generated explanation

The prototype uses a hybrid design:

- Deterministic Python code calculates facts and risk signals.
- The local LLM explains non-risk questions using supplied evidence.
- Risk questions are answered by the deterministic risk engine.

This is safer than asking the LLM to calculate everything.

### Supported deterministic risk signals

- Blocked open work.
- Overdue open work.
- Stale open work.
- Unassigned open work.
- Concentrated workload.
- Low completion rate.

An open issue is not automatically a risk. A completed issue is progress, not a
risk by itself.

### How hallucination control works

- The system prompt forbids invented facts and issue keys.
- User text is treated as data, not as system instructions.
- Model output must follow a JSON schema.
- Temperature is zero for more repeatable behavior.
- Returned issue keys are filtered against allowed evidence keys.
- Known missing-data limitations are appended by application code.
- Risk recommendations are generated deterministically from approved signals.

### Why the response includes limitations

Missing due dates, story points, labels, comments, or history affect what the
system can safely conclude. Reporting limitations is more professional than
pretending the evidence is complete.

### Local AI privacy and cost

`llama3.2` runs through Ollama on the local machine. No cloud model key is
required and Jira evidence is not sent to a third-party model API by this
prototype.

This does not automatically solve every security problem. Prototype JWT
authentication and viewer/admin authorization are implemented, while company
SSO, audit policy, device security, and production infrastructure remain future
work.

## Phase 6 — RAG and semantic search

### What RAG means

RAG stands for Retrieval-Augmented Generation.

Instead of asking a model to answer from its general training memory, the system
first retrieves project-specific Jira text. The model then answers using only
that retrieved context.

### Why RAG was needed after Phase 5

Phase 5 works well for structured facts such as counts and known risk signals.
It is less suitable for questions whose answer is hidden in descriptions or
comments and may use different wording.

For example:

- User wording: “The AI invents Jira issues that do not exist.”
- Actual ticket: `T1-22 — AI hallucinating missing tickets`.

These phrases are semantically related even though they are not exact keyword
matches.

### Chunking

Long text is split into bounded, overlapping chunks. Each chunk has a stable
SHA-256 identifier and traceable metadata:

- Project key.
- Issue key.
- Content type: summary, description, or comment.
- Source identifier.
- Chunk index.
- Source update time.
- Comment author when applicable.

Empty content is skipped. Stable identities support idempotent re-indexing.

### Embeddings

An embedding is a numeric vector representing the meaning of text. Texts with
related meaning should have vectors that are close together.

`nomic-embed-text` requires task prefixes:

- Indexed Jira text uses `search_document:`.
- User questions use `search_query:`.

The first live implementation omitted these prefixes. Retrieval worked but
ranking was poor. The official model usage was checked, the prefixes were added,
tests were created, and T1 was re-indexed.

### Vector storage and retrieval

Each chunk and its 768-dimensional vector are stored in PostgreSQL. Search:

1. Embeds the question.
2. Filters chunks by project key.
3. Calculates cosine distance.
4. Returns the closest bounded set with similarity scores and Jira metadata.

Project filtering is essential. Evidence from another project must not leak into
the answer.

### Why retrieve ten candidates

Raw vector ranking is useful but not perfect, especially for short summaries.
The difficult T1-22 query ranked sixth. A top-three search would miss it; a
top-ten candidate set contains it.

The grounded answer endpoint retrieves ten candidates and asks `llama3.2` to
select only evidence that directly supports the answer.

### Final RAG safety checks

- Only retrieved chunks are sent as evidence.
- The prompt forbids invented project details.
- Only issue keys present in retrieved candidates are accepted.
- Duplicate or unknown citations are removed.
- If no supported citation remains, the generated answer is replaced with an
  explicit insufficient-evidence response.

### Retrieval evaluation

The evaluation set contains five fixed T1 questions with expected issue keys.
The evaluation command reports:

- Recall@K: whether the expected issue appeared in the allowed top-K results.
- Mean Reciprocal Rank: how high the first correct result appeared on average.

Verified live results:

- 5 hits from 5 cases.
- Recall@K of `1.0`.
- Mean Reciprocal Rank of `0.8333`.
- Required gates were `0.8` Recall@K and `0.5` MRR.

Four expected tickets ranked first. The difficult hallucination query placed
T1-22 sixth but the grounded answer correctly selected and cited it.

## Important endpoint groups

### Health and documentation

- `GET /health`
- `GET /ready`
- `GET /docs`
- `GET /openapi.json`

### Live Jira access

- `GET /api/projects`
- `GET /api/boards`
- `GET /api/sprints/{board_id}`
- `GET /api/sprints/{sprint_id}/issues`
- `GET /api/users`
- `GET /api/issues/{project_key}`
- `GET /api/issues/detail/{issue_key}`
- `GET /api/issues/{issue_key}/comments`
- `GET /api/issues/{project_key}/search`

### Live analytics

- `GET /api/analytics/projects/{project_key}/overview`
- `GET /api/analytics/projects/{project_key}/activity`
- `GET /api/analytics/projects/{project_key}/insights`
- `GET /api/analytics/projects/{project_key}/history`
- `GET /api/analytics/projects/{project_key}/sprints`
- `GET /api/analytics/projects/{project_key}/status-counts`
- `GET /api/analytics/projects/{project_key}/priority-counts`
- `GET /api/analytics/projects/{project_key}/type-counts`
- `GET /api/analytics/projects/{project_key}/workload`
- `GET /api/analytics/projects/{project_key}/overdue`
- `GET /api/analytics/sprints/{sprint_id}/completion`
- `GET /api/analytics/sprints/{sprint_id}/performance`

### Synchronization and stored data

- `POST /api/sync/projects/{project_key}`
- `POST /api/sync/projects/{project_key}/incremental`
- `GET /api/sync/runs`
- `GET /api/sync/runs/{run_id}`
- `GET /api/stored/issues/{project_key}`
- `GET /api/stored/analytics/projects/{project_key}/overview`
- `GET /api/stored/analytics/projects/{project_key}/activity`
- `GET /api/stored/analytics/projects/{project_key}/insights`
- `GET /api/stored/analytics/projects/{project_key}/history`
- `GET /api/stored/analytics/sprints/{sprint_id}/performance`

### AI and RAG

- `POST /api/ai/projects/{project_key}/ask`
- `POST /api/rag/projects/{project_key}/index`
- `POST /api/rag/projects/{project_key}/search`
- `POST /api/rag/projects/{project_key}/ask`

## Difference between the two AI ask endpoints

`POST /api/ai/projects/{project_key}/ask` uses structured project evidence and
deterministic risk signals. It is appropriate for project summaries and delivery
risk questions.

`POST /api/rag/projects/{project_key}/ask` performs semantic retrieval over Jira
summaries, descriptions, and comments. It is appropriate for finding or
explaining unstructured ticket content.

They solve related but different problems. RAG does not replace deterministic
analytics.

Sprint-list and sprint-count questions must use
`GET /api/analytics/projects/{project_key}/sprints`. The RAG ask service detects
those structured questions and directs the caller to this deterministic endpoint
without running embeddings or the language model.

## Common commands you should know

Activate the environment:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

Start PostgreSQL:

```powershell
docker compose up -d postgres
docker compose ps
```

Apply migrations:

```powershell
python -m alembic upgrade head
python -m alembic current
```

Start the API:

```powershell
python -m uvicorn main:app
```

Run all tests:

```powershell
python -m pytest -q
```

Run retrieval evaluation while the API is running:

```powershell
python -m scripts.evaluate_rag
```

Inspect local models:

```powershell
ollama list
ollama ps
```

Never paste real Jira tokens or database passwords into documentation, commits,
screenshots, or chat messages.

## A safe demonstration sequence

1. Show `/health`, `/ready`, and `/docs`.
2. Fetch `/api/projects` to prove Jira connectivity.
3. Show a live project overview for T1.
4. Run or show a completed full synchronization record.
5. Show the stored overview to prove analytics can work without live Jira.
6. Ask the deterministic AI endpoint for delivery risks.
7. Search RAG for the hallucinated-ticket wording.
8. Show that raw retrieval places T1-22 within the candidates.
9. Call the grounded RAG ask endpoint and show the validated T1-22 citation.
10. Show the 84-test result and the retrieval evaluation metrics.

Do not perform destructive Jira operations during the demonstration. The current
prototype reads Jira and stores a local synchronized copy.

## Questions a supervisor may ask and strong answers

### “Why not let the AI calculate all metrics?”

Counts, dates, completion rates, and risk rules must be reproducible and
auditable. Python calculates those facts. AI is used only where language
understanding or explanation adds value.

For example, asking which sprints exist and how many issues each contains uses
the deterministic project sprint-summary endpoint. The RAG index contains issue
text, not authoritative sprint membership counts.

### “How do you prevent hallucinated Jira issues?”

The model receives only project-scoped evidence, output follows a JSON schema,
and every cited issue key is checked against the evidence or retrieved candidate
set. Unknown keys are removed. If no supported citation remains, the RAG answer
is replaced with an insufficient-evidence response.

If the user explicitly names a key such as T1-22, the system does not use vector
similarity at all. It performs an exact project-scoped PostgreSQL lookup and
returns deterministic synchronized fields. This prevents a semantically similar
issue from replacing the issue the user actually requested.

Questions that ask which issues "mention," "discuss," or are "related to" a
topic use bounded semantic ranking but do not ask the language model to rewrite
the ranking. This prevents a generated answer from contradicting its own source
list. Open explanatory questions may still use the local model, but citations
are removed whenever its answer claims that evidence is insufficient.

Vector similarity by itself can produce a confident-looking false positive. The
search path therefore also requires a meaningful query word to match the issue
text, using conservative fuzzy comparison for simple typos. Matching candidates
are reranked by supported-word count before vector score. Informal unassigned and
workload questions bypass RAG and use synchronized assignment fields. The UI
shows only evidence cited by the accepted answer, not every raw candidate.

### “Does grounded mean the AI is always correct?”

No. Grounding reduces unsupported answers by restricting evidence and validating
citations. It does not guarantee that the model interprets every evidence passage
correctly. That is why we also expose limitations and measure retrieval quality.

### “Why use a local model?”

It is free for the prototype, avoids a cloud API key, and keeps Jira evidence on
the local machine. The tradeoffs are hardware limits, slower generation, and
possibly lower quality than large cloud models.

### “Can the model be replaced?”

Yes. Model access is isolated behind the Ollama client and environment settings.
A compatible local model can be selected through configuration. A cloud provider
would require a new client adapter and security review, but the service and
evidence architecture would remain mostly unchanged.

### “Why PostgreSQL instead of only SQLite?”

SQLite is excellent for lightweight tests and simple local development.
PostgreSQL is more appropriate for concurrent, production-like storage and
supports pgvector for semantic retrieval.

### “Why not use a separate vector database?”

pgvector lets the prototype keep relational Jira data and embeddings in one
operational database. That simplifies deployment, transactions, backups, and
project filtering. A dedicated vector database may be justified later at much
larger scale.

### “What makes synchronization idempotent?”

Projects, issues, changelogs, comments, and chunks use stable Jira or generated
identities. Repeated syncs update matching rows. Sprint links and comment
snapshots replace stale membership instead of accumulating duplicates.

### “What happens when Jira is unavailable?”

Live Jira routes return sanitized timeout or connection errors. Previously
synchronized database routes, deterministic analytics, and indexed RAG evidence
can still operate using stored data.

### “Why have live and stored analytics endpoints?”

Live endpoints are useful for immediate Jira verification. Stored endpoints are
faster, reduce Jira dependence, support history, and provide consistent evidence
for AI. In a mature product, stored reads would normally be the default user
experience after scheduled synchronization.

### “How do you know more than 50 Jira issues are handled?”

The Jira client follows each endpoint's actual pagination contract until the
last page or token. Automated tests simulate multi-page responses, including
more than 50 issues.

### “What is Recall@K?”

It measures whether at least one expected relevant result appears within the top
K candidates. The live evaluation achieved 1.0, meaning all five expected issues
appeared within their configured limits.

### “What is Mean Reciprocal Rank?”

For each question, take one divided by the rank of the first correct result, then
average those values. First place scores 1.0; sixth place scores about 0.1667.
The final average was 0.8333.

### “Why was T1-22 only sixth?”

The index currently contains mostly very short summaries and few descriptions
or comments. Short text provides limited semantic context. The top-ten grounded
answer still selected the correct issue. Future improvements could include richer
descriptions, more real comments, hybrid keyword/vector retrieval, or reranking.

### “How is this different from a generic Jira chatbot?”

This prototype combines custom deterministic metrics, organization-controlled
risk rules, synchronized historical storage, local models, project-isolated RAG,
validated citations, and measurable retrieval evaluation. Its focus is
auditability and the team's specific engineering workflow.

### “Why were comments added if T1 has zero comments?”

The enterprise use case requires comment evidence even though the current test
project has none. Non-empty comment behavior is verified with controlled tests,
and the live synchronization correctly reports zero rather than inventing data.

### “Why is caching not implemented?”

Stored PostgreSQL reads already solve the repeated-network-call problem. No
measured latency currently justifies cache invalidation complexity. Caching can
be added after profiling demonstrates a real bottleneck.

## Honest limitations you should mention

- Local JWT authentication and viewer/admin authorization are implemented.
- The current API should still not be publicly exposed; production identity must
  use company SSO/OIDC and production-grade infrastructure.
- T1 is a small evaluation project with 20 issues.
- T1 currently has no real comments, due dates, labels, or story-point estimates
  in several evaluated contexts.
- Retrieval evaluation contains only five cases and should grow with real team
  questions.
- Raw semantic ranking is imperfect for very short summaries.
- Synchronization is manually triggered; scheduling is future work.
- Rate limiting and restrictive CORS are future phases.
- The Starlette TestClient/httpx deprecation warning is known and non-blocking.
- A user-facing React dashboard, safe demo, and major viewer flows are
  production-build and browser verified; deployment and automated end-to-end
  browser tests remain.
- Production monitoring, backups, CI/CD, and deployment hardening remain.

Admitting limitations demonstrates engineering maturity. Do not claim the
prototype is production-ready.

## Security rules you must remember

- Never commit `.env` or `.env.postgres`.
- Never expose Jira API tokens or database passwords.
- Do not log Jira response bodies containing sensitive issue content.
- Do not return raw connection exceptions to API users.
- Treat user questions and Jira text as untrusted data.
- Filter data by project before AI retrieval.
- Keep the prototype on trusted, private infrastructure; Phase 12 hardening does
  not replace production SSO, TLS, central audit logging, or secret management.

## What is complete and what comes next

Completed and verified:

- Phase 1: backend stabilization and Jira integration.
- Phase 2: deterministic analytics.
- Phase 3: safe filtering, sorting, and pagination.
- Phase 4: persistence and synchronization.
- Phase 5: grounded AI assistant.
- Phase 6: RAG, pgvector, grounded answers, comments, and retrieval evaluation.
- Phase 7: JWT authentication, Argon2 hashing, company/project/team
  authorization, restrictive CORS, and prototype rate limiting.
  Optional first name, last name, and email profiles now identify real people;
  the dashboard calls the `viewer` role **Team Member** while the backend retains
  the stable authorization value.
- Phase 8: test-completeness review, PostgreSQL integration tests, security and
  evidence negative paths, and an 80% coverage gate.
- Phase 9: Ruff, mypy, and local pre-commit configuration; removal of
  unreferenced placeholder modules; focused API routers; protected local data
  artifacts; repaired Python 3.12 virtual environment; zero lint/type findings;
  all API paths preserved; and a current 83.85% coverage result above the 80%
  gate.
- Phase 10: protected viewer/admin navigation, stored overview analytics, issue
  explorer, sprint portfolio and detail, risk center, team workload, grounded AI
  supporting Jira evidence, administrator sync controls and progress, freshness and RAG
  status, notifications, clickable Jira keys, safe synthetic demo, responsive
  styling, route-level code splitting, twelve passing frontend tests,
  successful production build, and completed desktop browser verification.
  Active dashboards now check the selected project's completed sync marker every
  15 seconds. A new administrator sync invalidates cached project data, refetches
  it for every open user session, and briefly displays **Project data updated**.
  Jira Knowledge also recognizes structured questions about priority, status,
  assignee, and issue type. Those answers come directly from synchronized fields,
  cite exact matching issue keys, and do not call embeddings or the language model.

Phase 11 is also complete:

- Phase 11: non-root FastAPI and React/Nginx images, PostgreSQL/pgvector,
  automatic Alembic migration gating, health checks, local Ollama connectivity,
  localhost-only ports, and documented backup/restore/rollback operations.
- Phase 12: secrets and dependency audits, measured request-body limits,
  no-store API responses, browser security headers, dashboard CSP, authorization
  and prompt-injection regression tests, privacy review, and a documented threat
  model. No known Python runtime or npm production vulnerabilities were found.

The repository roadmap continues with Phase 13:

- Git and portfolio quality.

The final permission-aware UI refinement uses one shared dashboard with three
effective interface roles: company administrator, project administrator for the
selected project, and team member. Users see only relevant navigation, receive a
first-login role guide, can reopen that guide from the header, and see contextual
reminders that the platform is read-only and Jira remains the source of truth.
This is a usability layer over enforced backend authorization, not a replacement
for it.

The final internship work must also include the report, presentation, architecture
diagrams, screenshots, and a rehearsed demonstration.

## Final mental model

Remember this sentence:

> Jira is the source, synchronization creates a reliable local memory,
> deterministic code calculates facts, vector search retrieves meaning, and the
> local AI explains only the evidence it is allowed to see.

## How the deployment works

Docker solves the "it works on my machine" problem by fixing the operating
system, language runtime, dependencies, startup command, and network wiring for
each component. Compose then starts those components in a safe order.

The PostgreSQL health check must pass first. A short-lived migration container
then applies the Alembic schema. Only a successful migration permits FastAPI to
start. Nginx waits for FastAPI to become healthy before serving the compiled
dashboard. Ollama remains on the company-controlled host and is reached through
Docker Desktop's host gateway.

The browser talks to Nginx. Nginx serves React and forwards `/api`, `/health`,
`/ready`, and API documentation requests to FastAPI. FastAPI reads synchronized
facts from PostgreSQL, contacts Jira only for approved live operations, and
contacts Ollama only for local generation or embeddings.

This deployment is intentionally private. Binding ports to `127.0.0.1` means
other computers cannot reach the prototype directly. Company-wide deployment
still requires SSO/OIDC, TLS, managed secrets, centralized monitoring, managed
backups, and the final security review.

The detailed operator commands are in `docs/deployment.md`.

If you understand that sentence and can explain each part, you understand the
completed project.
