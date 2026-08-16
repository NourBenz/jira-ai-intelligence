# Jira AI Intelligence — Project Structure Guide

This document explains how the Jira AI Intelligence repository is organized,
why this structure was chosen, and what every meaningful project-owned file is
responsible for. It describes the repository as it exists now. Generated files,
dependency folders, local databases, caches, secrets, and build artifacts are
described separately because they are not application source code.

No directory should be understood in isolation. Jira data enters through the
integration layer, is normalized and synchronized into persistence, is analyzed
by deterministic services, may be retrieved by the RAG layer, is exposed through
authenticated API routes, and is finally displayed by the React interface.

## Why the repository uses this structure

The project follows a layered architecture. The main reason is separation of
responsibilities: code that contacts Jira should not also calculate analytics,
write database records, build HTTP responses, and render the user interface.

The structure provides these benefits:

- **Maintainability:** a developer can find configuration, Jira integration,
  analytics, synchronization, security, AI, or UI code without searching one
  very large file.
- **Testability:** business rules can be tested with fake Jira data without a
  real Jira connection, while database and API behavior can be tested separately.
- **Security:** authentication, authorization, request limits, secrets, and
  upstream error sanitization have clear boundaries.
- **Replaceability:** the React interface can later be wrapped by Electron, the
  Ollama model can be changed, and PostgreSQL can be hosted elsewhere without
  rewriting the analytics rules.
- **Reliable AI:** deterministic analytics and stored Jira evidence are prepared
  before an LLM is allowed to explain them.
- **Clear ownership:** routes handle HTTP, services handle use cases, repositories
  handle persistence, schemas define contracts, and components handle display.

The dependency direction is intentionally close to this:

```text
React interface
    ↓ HTTP
FastAPI routes and dependencies
    ↓
Application services
    ↓
Jira client / repositories / AI and RAG adapters
    ↓
Jira Cloud / PostgreSQL-pgvector / Ollama
```

## High-level repository map

```text
jira-ai-intelligence/
├── app/                     FastAPI backend application
├── migrations/              Versioned database schema changes
├── scripts/                 Operator and maintenance commands
├── tests/                   Backend automated verification
├── frontend/                React and TypeScript user interface
├── docs/                    Focused engineering documentation
├── evaluation/              Repeatable RAG evaluation cases
├── main.py                  FastAPI process entry point
├── compose.yaml             Complete local deployment definition
├── Dockerfile               Backend container definition
├── requirements*.txt        Python dependency definitions
├── pyproject.toml           Python quality-tool configuration
├── README.md                Main project journal and phase tracker
├── KEEPUP.md                Project-defense and learning guide
└── PROJECT_STRUCTURE.md      This structure guide
```

## Root-level files

### `main.py`

This is the backend entry point. It creates the FastAPI application, configures
safe logging, installs CORS and security middleware, mounts authentication and
business routers, and exposes `/health` and `/ready`. It should remain small: its
job is application composition rather than Jira or analytics logic.

### `compose.yaml`

This defines the reproducible local system. It starts PostgreSQL with pgvector,
runs Alembic migrations in a temporary migration container, starts FastAPI only
after migration succeeds, and starts the Nginx frontend after the backend is
healthy. It also connects the backend container to host-managed Ollama.

### `Dockerfile`

This builds the backend image from Python 3.12. It installs only runtime
dependencies, copies the application and migrations, creates a non-root user,
and starts through the safe Docker entrypoint. Running as a non-root user reduces
the impact of a container compromise.

### `alembic.ini`

This configures Alembic, identifies the `migrations/` directory, provides the
SQLite development default, and defines migration logging. The effective
database URL can be replaced by application environment configuration.

### `requirements-runtime.txt`

This is the minimal dependency set required to run the API: FastAPI, Uvicorn,
Pydantic, Requests, SQLAlchemy, Alembic, PostgreSQL/pgvector drivers, JWT support,
and Argon2 password hashing.

### `requirements.txt`

This includes `requirements-runtime.txt` and adds development tools such as
pytest, coverage, Ruff, mypy, pre-commit, Bandit, and pip-audit. Production
containers intentionally use the smaller runtime file.

### `pyproject.toml`

This contains the Python quality policy. It configures Ruff linting/formatting
and strict-enough mypy checks for the application, entry point, and scripts.

### `.coveragerc`

This defines backend coverage measurement and enforces an 80 percent minimum for
`app` and `main` while excluding intentionally non-executable branches.

### `.pre-commit-config.yaml`

This runs Ruff linting, Ruff formatting checks, and mypy before a commit when
pre-commit is installed. It catches common mistakes before they enter history.

### `.gitignore`

This keeps secrets, virtual environments, caches, generated JavaScript,
coverage output, local databases, backups, and build output out of Git.

### `.dockerignore`

This keeps development-only and sensitive files out of the backend Docker build
context. A smaller context produces faster builds and reduces accidental secret
inclusion.

### `.env.example`

This documents safe placeholder configuration for Jira, database, JWT, Ollama,
request limits, and related backend settings. It may be committed because it
contains examples rather than real secrets.

### `.env.postgres.example`

This is the template for PostgreSQL container credentials and connection
settings. The real `.env.postgres` remains local and ignored.

### `README.md`

This is the main project document and living engineering journal. It explains
the problem, architecture, technologies, phases, decisions, verification, and
report evidence collected throughout the internship.

### `KEEPUP.md`

This is the learning and project-defense guide. It explains the system in plain
language and prepares the student for supervisor questions, technical interviews,
the report, and the demonstration.

## Backend application: `app/`

The `app/` directory contains all backend application code. Its subdirectories
represent distinct architectural responsibilities.

### `app/__init__.py`

Marks `app` as a Python package and documents the backend package boundary.

## AI provider layer: `app/ai/`

This layer communicates with the text-generation model. It does not retrieve
Jira data itself.

### `app/ai/ollama_client.py`

Defines the Ollama HTTP client used for structured, non-streaming local model
responses. It validates model output through Pydantic and converts timeouts or
invalid responses into sanitized application errors.

## HTTP layer: `app/api/`

The API layer translates HTTP requests into service calls. Routes validate input,
apply dependencies, select response schemas, and map missing resources to HTTP
responses. Business calculations should not be implemented here.

### `app/api/routes.py`

Composes all authenticated business routers under one parent router protected by
the viewer dependency. Authentication routes are mounted separately by `main.py`
because login must be reachable before a token exists.

### `app/api/dependencies.py`

Defines FastAPI dependency injection for database sessions, Jira and RAG
services, authenticated users, company administrators, project access, project
administration, sprint/issue access, validated project keys, and rate limits.
This file is a central security boundary.

### `app/api/auth_routes.py`

Implements login and `/auth/me`. It performs constant-work password verification,
returns generic authentication failures, creates JWTs, and returns the current
user plus administered project keys.

### `app/api/access_routes.py`

Implements company-administration operations for Scrum teams, users, project
ownership, membership responsibilities, project administrators, and project
access summaries.

### `app/api/jira_routes.py`

Exposes authorized live Jira reads and searches, including boards, sprints,
issues, comments, users, safe client configuration, and accessible stored
projects. These routes use validated filters and project/issue access checks.

### `app/api/analytics_routes.py`

Exposes deterministic analytics calculated from live Jira data: counts,
workload, overdue work, overview, activity, insights, history, sprint summaries,
completion, and performance.

### `app/api/stored_routes.py`

Exposes database-backed issue and analytics reads. These stored-first routes make
the dashboard responsive and consistent without contacting Jira for every view.

### `app/api/sync_routes.py`

Exposes full and incremental synchronization, update checks, freshness status,
sync history, and issue-level sync details. Mutating synchronization operations
require company or project administration.

### `app/api/intelligence_routes.py`

Exposes deterministic AI risk answers, RAG indexing, index status, semantic
search, and grounded project questions. It applies project access and stricter
rate limits to expensive operations.

## Core infrastructure: `app/core/`

Core modules provide cross-cutting configuration and security behavior used by
multiple application layers.

### `app/core/__init__.py`

Marks the core infrastructure directory as a Python package.

### `app/core/config.py`

Defines typed Pydantic settings for Jira, database, JWT, Ollama, embeddings,
CORS, and request limits. It validates unsafe or incomplete configuration early
and caches the resulting settings object.

### `app/core/logging.py`

Configures consistent application logging without printing secrets or raw Jira
responses.

### `app/core/middleware.py`

Implements request-body size enforcement and API security headers. Limits are
measured even for chunked bodies without a `Content-Length` header.

### `app/core/rate_limit.py`

Provides the in-memory sliding-window rate limiter used to protect login, AI,
and administrative operations in the single-instance prototype.

### `app/core/security.py`

Owns Argon2 password hashing and verification plus JWT creation and decoding.
Authentication cryptography is deliberately separated from route logic.

## Persistence layer: `app/database/`

This layer maps application data to SQLAlchemy and centralizes database access.

### `app/database/__init__.py`

Re-exports the database base, entities, engine/session helpers, and repositories
to provide a convenient database package interface.

### `app/database/base.py`

Defines the SQLAlchemy declarative base and stable constraint-naming conventions
used by entities and Alembic migrations.

### `app/database/entities.py`

Defines persisted entities for projects, issues, sprints, sprint membership,
changelogs, comments, sync runs, sync changes, RAG chunks, users, Scrum teams,
team memberships, and project-administrator grants.

### `app/database/session.py`

Creates SQLite or PostgreSQL engines, session factories, and FastAPI-managed
database sessions from typed configuration.

### `app/database/repositories.py`

Contains persistence operations. `JiraRepository` performs idempotent Jira-data
upserts, sync tracking, access-supporting queries, and stored retrieval.
`RAGRepository` persists embeddings, performs pgvector search, and reports index
status. Repositories prevent SQL details from leaking throughout services.

## Jira integration: `app/jira/`

### `app/jira/jira_client.py`

This is the low-level Jira Cloud REST adapter. It authenticates requests,
sanitizes upstream errors, paginates offset/token/array response styles, builds
safe JQL from trusted values, retrieves changelogs and comments, and cleans raw
Jira issues into the application’s stable structure.

## Domain models: `app/models/`

### `app/models/ticket.py`

Defines the normalized Pydantic `Ticket` model used across Jira, analytics,
storage, API responses, and RAG. This keeps deeply nested Jira response details
out of the rest of the application.

## RAG layer: `app/rag/`

The retrieval-augmented generation layer converts stored Jira evidence into
searchable vectors and evaluates retrieval quality.

### `app/rag/chunker.py`

Normalizes Jira summaries/descriptions, splits them deterministically with safe
overlap, creates stable chunk IDs, and attaches project/issue metadata required
for traceability.

### `app/rag/embeddings.py`

Calls Ollama’s embedding endpoint, distinguishes document and query prefixes,
validates vector dimensions/counts, and sanitizes embedding failures.

### `app/rag/vector_store.py`

Provides the pgvector storage/search adapter. It validates vector dimensions,
performs project-scoped similarity search, and returns typed search results.

### `app/rag/evaluation.py`

Loads retrieval test cases and calculates Recall@K and Mean Reciprocal Rank so
RAG quality is measured rather than judged only by demonstrations.

## API contracts: `app/schemas/`

Schemas define validated request and response contracts. They protect the
application from invalid input and make OpenAPI documentation precise.

### `app/schemas/__init__.py`

Marks the schemas directory as a Python package.

### `app/schemas/access.py`

Defines Scrum-team, membership, project-team, project-administrator, user, and
project-access summary contracts.

### `app/schemas/auth.py`

Defines constrained login input, token output, user roles, and the current-user
response including profile and administered-project information.

### `app/schemas/project.py`

Defines the small project response containing Jira ID, key, and name.

### `app/schemas/search.py`

Defines allowlisted issue-search filters, validated sorting/paging input, and
cursor-based search responses.

### `app/schemas/analytics.py`

Defines contracts for overview, activity, insights, history, overdue work,
sprint completion, sprint summaries, and sprint performance.

### `app/schemas/sync.py`

Defines sync-run, issue-level change, run-detail, and freshness/update responses.

### `app/schemas/ai.py`

Defines project-question input and deterministic AI answer output containing
risks, recommendations, sources, limitations, model identity, and grounding.

### `app/schemas/rag.py`

Defines RAG indexing, status, search, retrieved result, question, and grounded
answer contracts.

## Business/use-case layer: `app/services/`

Services coordinate domain behavior. They may combine repositories, the Jira
facade, analytics, or model adapters, but they do not render HTTP or UI output.

### `app/services/jira_service.py`

Provides the application-facing Jira facade. It combines `JiraClient` retrieval
with analytics calculations and exposes stable operations to routes and sync.

### `app/services/analytics_service.py`

Contains deterministic calculations for counts, overdue/stale/blocked work,
overview, activity, insights, historical throughput, lead/cycle time, sprint
completion, velocity, scope change, and carryover.

### `app/services/stored_data_service.py`

Reconstructs normalized tickets and analytics from synchronized database data.
It powers stored-first dashboard reads and exact project-scoped issue lookup.

### `app/services/sync_service.py`

Orchestrates full and incremental Jira synchronization, database upserts,
changelogs, comments, sprints, issue membership, change auditing, counts,
watermarks, transactions, and sanitized failure records.

### `app/services/sync_observability_service.py`

Compares Jira’s latest update marker with the synchronized project snapshot,
caches lightweight checks, and records whether users should be notified that a
sync is required.

### `app/services/access_service.py`

Implements the one-company project-access model: accessible projects, owning
Scrum teams, user memberships, Scrum responsibilities, company administrators,
and per-project administration grants.

### `app/services/evidence_service.py`

Builds bounded, deterministic project evidence and delivery-risk signals from
stored data. It records missing fields as limitations rather than inventing risk.

### `app/services/ai_service.py`

Routes structured questions to deterministic stored facts and constructs
auditable risk answers. It constrains model output to supplied signals, validates
citations, and applies limitations when evidence is incomplete.

### `app/services/question_router.py`

Recognizes explicit issue keys, structured issue-field questions, sprint totals,
unassigned/workload analytics, and semantic-search intent. It tolerates informal
phrasing and some typos while preventing every question from becoming an
uncontrolled model call.

### `app/services/rag_service.py`

Orchestrates indexing, embeddings, vector retrieval, exact issue lookup,
structured routing, deterministic semantic matching, reranking, grounded Ollama
answers, project scoping, citation filtering, and insufficient-evidence handling.

## Database migrations: `migrations/`

Migrations are an ordered, auditable history of database changes. Application
startup applies them before the backend is considered ready.

### `migrations/env.py`

Connects Alembic to application metadata and the configured database URL, and
supports both online and offline migration modes.

### `migrations/script.py.mako`

This is Alembic’s template for generating future migration files.

### `migrations/versions/20260712_01_initial_schema.py`

Creates the initial projects, issues, sprints, changelogs, sync runs, and core
persistence schema. Sprint-to-issue membership is added by the next revision.

### `migrations/versions/20260713_02_sprint_issue_membership.py`

Adds or refines persisted issue membership for synchronized sprints.

### `migrations/versions/20260713_03_rag_vector_storage.py`

Enables pgvector support and creates project-scoped vector storage for RAG
chunks.

### `migrations/versions/20260714_04_persist_jira_comments.py`

Adds synchronized Jira comments so they can become traceable RAG evidence.

### `migrations/versions/20260723_05_add_application_users.py`

Adds local prototype users, roles, password hashes, and account status for JWT
authentication and role-based authorization.

### `migrations/versions/20260803_06_add_user_profiles.py`

Adds optional first name, last name, and unique email profile fields.

### `migrations/versions/20260805_07_add_project_team_access.py`

Adds Scrum teams, memberships, project ownership, Scrum responsibilities, and
per-project administrator grants.

### `migrations/versions/20260805_08_add_sync_observability.py`

Adds project update-check markers and issue-level synchronization change records.

## Operator scripts: `scripts/`

Scripts are explicit operational commands rather than request-time application
logic.

### `scripts/__init__.py`

Marks scripts as a package so commands can be run with `python -m scripts...`.

### `scripts/create_user.py`

Interactively creates a local platform account, validates profile information,
hashes the password, rejects duplicates, and stores the selected viewer/admin
role.

### `scripts/docker_entrypoint.py`

Safely constructs the effective container database URL from Docker environment
variables, handles password URL encoding, and launches the requested container
command.

### `scripts/evaluate_rag.py`

Runs the fixed retrieval dataset through the current RAG search pipeline and
prints Recall@K, Mean Reciprocal Rank, ranks, and returned issue keys.

## Backend tests: `tests/`

Tests use controlled fake data for deterministic behavior and protect against
regressions without altering real company Jira data.

### `tests/test_jira.py`

Verifies issue cleaning, safe JQL, pagination, comments, changelogs, cursors,
watermarks, timeouts, connection failures, permissions, authentication errors,
invalid JSON, and sanitized unexpected Jira failures.

### `tests/test_analytics.py`

Verifies counts, workload, completion, status categories, overdue/stale logic,
large result sets, overview/activity/insights, historical metrics, velocity,
cycle time, sprint scope change, and sprint summaries.

### `tests/test_api.py`

Verifies dependency-injected routes, health/readiness, safe client configuration,
search validation, sprint summaries, RAG endpoints, and missing-evidence errors.

### `tests/test_auth.py`

Verifies Argon2, login, JWT validation/expiration, disabled users, changed roles,
generic failures, CORS, rate limits, and viewer/admin operation boundaries.

### `tests/test_project_access.py`

Verifies team-scoped project visibility, immediate revocation, project-admin
scope, company-only access management, malicious keys, and cross-project denial.

### `tests/test_database.py`

Verifies SQLAlchemy metadata, persistence tables, access tables, and optional
unique profile fields.

### `tests/test_postgres.py`

Provides opt-in PostgreSQL smoke tests for real connectivity and project-scoped,
idempotent pgvector search.

### `tests/test_sync.py`

Verifies full and incremental sync, idempotency, watermarks, updates, fallback
behavior, sanitized failures, issue-level change details, and freshness checks.

### `tests/test_stored_data.py`

Verifies stored issues, exact lookup, database-backed analytics, sprint
performance, comments, and the guarantee that stored endpoints do not construct
live Jira services.

### `tests/test_ai.py`

Verifies deterministic routing, grounded risk construction, limitations,
prompt-injection treatment, citation filtering, Ollama request format, timeouts,
and invalid model responses.

### `tests/test_rag.py`

Verifies chunking, embeddings, vector validation, indexing, project scoping,
exact lookup, semantic retrieval, reranking, typo tolerance, structured routing,
prompt-injection resistance, citations, and insufficient evidence.

### `tests/test_rag_evaluation.py`

Verifies retrieval-case validity and the Recall@K/MRR metric implementation.

### `tests/test_evidence.py`

Verifies that supported delivery-risk signals are constructed from facts and
missing fields become limitations rather than invented risks.

### `tests/test_config.py`

Verifies typed settings, required Jira values, dependency injection, safe CORS,
and request-body limit validation.

### `tests/test_security.py`

Verifies no-store/security headers and oversized request rejection, including
chunked requests without content length.

### `tests/test_docker_entrypoint.py`

Verifies safe container database URL construction and encoded passwords.

## Frontend application: `frontend/`

The frontend is a protected React and TypeScript single-page application. It
uses stored data for most dashboards and calls live/administrative endpoints only
where needed. It remains read-only with respect to Jira issue editing.

### Frontend root files

#### `frontend/package.json`

Defines React, TanStack Query, Wouter, Recharts, Lucide icons, Vite, TypeScript,
Vitest, Testing Library, and the frontend build/test scripts.

#### `frontend/package-lock.json`

Locks exact npm dependency versions for reproducible clean installations and
container builds. It is generated but intentionally committed.

#### `frontend/index.html`

Provides the minimal HTML document and React mount element used by Vite.

#### `frontend/vite.config.ts`

Configures React, Tailwind processing, the development server, proxies to local
FastAPI, and the jsdom/Vitest test environment.

#### `frontend/tsconfig.json`

Coordinates the application and Vite configuration TypeScript projects.

#### `frontend/tsconfig.app.json`

Defines strict browser/application TypeScript compilation settings.

#### `frontend/tsconfig.node.json`

Defines TypeScript settings for Node-side tooling such as Vite configuration.

#### `frontend/Dockerfile`

Uses a Node build stage to compile React, then copies static output into a small
unprivileged Nginx image.

#### `frontend/nginx.conf`

Serves the single-page application, supplies SPA fallback routing, proxies API
and health requests to FastAPI, and defines the container health endpoint.

#### `frontend/security_headers.conf`

Defines browser protections such as Content Security Policy, frame restrictions,
referrer policy, and content-type protections for Nginx responses.

#### `frontend/.env.example`

Documents the optional `VITE_API_URL`. It remains empty in normal local
development so Vite or Nginx can proxy relative API requests.

#### `frontend/.dockerignore`

Excludes local dependencies, builds, logs, environment files, and unnecessary
Docker metadata from the frontend build context.

### Frontend entry and routing

#### `frontend/src/main.tsx`

Bootstraps React, TanStack Query, authentication context, and global styles, then
mounts the application into `index.html`.

#### `frontend/src/App.tsx`

Defines protected, lazy-loaded client routes. It redirects anonymous users to
login and ensures Data Sync is rendered only for administrators of the currently
selected project.

#### `frontend/src/styles.css`

Contains the complete responsive visual system for login, navigation, charts,
tables, AI, synchronization, role guidance, mobile layouts, and print/PDF output.

#### `frontend/src/vite-env.d.ts`

Adds Vite’s browser and environment-variable type declarations to TypeScript.

### Frontend API layer: `frontend/src/api/`

#### `frontend/src/api/client.ts`

Centralizes API base URL handling, bearer-token storage, JSON requests, demo
interception, and normalized API errors.

#### `frontend/src/api/types.ts`

Defines TypeScript versions of backend contracts for users, projects, tickets,
analytics, sprints, sync, access, AI, RAG, and client configuration.

#### `frontend/src/api/demo.ts`

Provides safe synthetic project data and intercepted endpoint responses for an
internship demonstration without exposing company Jira data.

#### `frontend/src/api/client.test.ts`

Verifies token-aware API requests and normalized client behavior.

#### `frontend/src/api/demo.test.ts`

Verifies deterministic safe-demo responses.

### Authentication: `frontend/src/auth/`

#### `frontend/src/auth/AuthContext.tsx`

Owns login, logout, token restoration, current-user loading, demo identity, and
the authentication state shared across pages.

#### `frontend/src/auth/userDisplay.ts`

Formats names/initials and derives the effective interface role—company admin,
project admin for the selected project, or team member—from real permissions.

#### `frontend/src/auth/userDisplay.test.ts`

Verifies display fallbacks and selected-project role derivation.

### Shared components: `frontend/src/components/`

#### `frontend/src/components/AppShell.tsx`

Provides the sidebar, permission-aware navigation, project selector, top bar,
user summary, responsive menu, and content/error/empty-state frame.

#### `frontend/src/components/HeaderTools.tsx`

Displays the role-guide trigger, demo control, synchronized-data freshness,
automatic update detection, query refresh after shared sync, and notification
popover.

#### `frontend/src/components/RoleGuide.tsx`

Explains current capabilities and read-only restrictions for company admins,
project admins, and team members. It supports first-login and reusable guidance.

#### `frontend/src/components/RoleGuide.test.tsx`

Verifies project-administrator guidance and the Jira read-only boundary.

#### `frontend/src/components/AccessManagement.tsx`

Provides company-admin controls for teams, membership responsibilities, project
ownership, and project-administrator grants.

#### `frontend/src/components/JiraIssueLink.tsx`

Creates safe links from displayed issue keys to their original Jira issue pages.

#### `frontend/src/components/MetricCard.tsx`

Renders reusable dashboard metric cards with icons, values, details, and tones.

#### `frontend/src/components/MetricCard.test.tsx`

Verifies metric-card content rendering.

#### `frontend/src/components/PageHeader.tsx`

Provides consistent page eyebrow, title, description, and action layout.

#### `frontend/src/components/States.tsx`

Provides reusable loading, error, and empty-state panels with accessible roles.

### Project selection: `frontend/src/project/`

#### `frontend/src/project/ProjectContext.tsx`

Loads authorized projects, remembers the selected project, prevents selection of
revoked projects, and coordinates safe demo mode.

### Reusable hooks: `frontend/src/hooks/`

#### `frontend/src/hooks/useElapsed.ts`

Tracks elapsed seconds for visible long-running synchronization or indexing
operations.

#### `frontend/src/hooks/useProjectSignals.ts`

Fetches and groups shared overview, activity, and insights queries used by the
dashboard header and project pages.

### Pages: `frontend/src/pages/`

#### `frontend/src/pages/LoginPage.tsx`

Provides protected account login and a separate safe-demo entry point.

#### `frontend/src/pages/OverviewPage.tsx`

Displays stored project totals, completion, status mix, history, workload,
delivery signals, and CSV/PDF export controls.

#### `frontend/src/pages/IssuesPage.tsx`

Displays the synchronized backlog with search, status filtering, Jira links,
assignee/priority/update information, exports, and read-only guidance.

#### `frontend/src/pages/SprintsPage.tsx`

Displays project sprints, dates, states, issue counts, and completion, and links
to detailed sprint pages.

#### `frontend/src/pages/SprintDetailPage.tsx`

Displays stored sprint performance, scope/carryover information, and sprint issue
membership.

#### `frontend/src/pages/RiskCenterPage.tsx`

Displays deterministic overdue, blocked, stale, unassigned, and workload
concentration signals without asking a model to invent risk.

#### `frontend/src/pages/TeamPage.tsx`

Displays workload by assignee and status through charts and teammate cards.

#### `frontend/src/pages/AssistantPage.tsx`

Separates Jira Knowledge from deterministic Delivery Risks, provides example
questions, sends grounded requests, and displays citations, evidence,
recommendations, and limitations.

#### `frontend/src/pages/AdminPage.tsx`

Provides full/incremental sync, Jira update checks, RAG indexing, progress,
freshness warnings, shared sync history, issue-level change details, and
company-only access management.

#### `frontend/src/pages/NotFoundPage.tsx`

Provides a controlled fallback for unknown client routes.

### Frontend utilities: `frontend/src/utils/`

#### `frontend/src/utils/evidence.ts`

Filters retrieved evidence so only Jira content matching answer citations is shown.

#### `frontend/src/utils/evidence.test.ts`

Verifies evidence/citation filtering.

#### `frontend/src/utils/export.ts`

Creates correctly escaped CSV downloads and invokes browser print/PDF output.

#### `frontend/src/utils/export.test.ts`

Verifies CSV escaping and generation.

#### `frontend/src/utils/syncFreshness.ts`

Detects whether a newly completed shared sync should refresh cached project data.

#### `frontend/src/utils/syncFreshness.test.ts`

Verifies initial-load and later-sync detection behavior.

### Frontend test setup: `frontend/src/test/`

#### `frontend/src/test/setup.ts`

Loads Testing Library’s DOM assertions and resets browser-like state between
Vitest tests.

## RAG evaluation data: `evaluation/`

### `evaluation/rag_retrieval_cases.json`

Contains the repeatable project questions, expected issue keys, and retrieval
depth used by `scripts/evaluate_rag.py`. Keeping evaluation cases outside code
makes the quality evidence reviewable and extendable.

## Documentation: `docs/`

### `docs/architecture.md`

Explains runtime components, data flow, trust boundaries, synchronization,
authorization, AI/RAG, and deployment architecture.

### `docs/api.md`

Documents endpoint groups, authentication, request/response behavior, and API
usage for developers and testers.

### `docs/postman-get-routes.md`

Provides copyable GET routes and Postman notes for manual API verification.

### `docs/dashboard.md`

Explains dashboard pages, role-aware behavior, demo flow, verification, and user
experience decisions.

### `docs/deployment.md`

Documents Docker Compose startup, migrations, environment configuration, health,
ports, Ollama, troubleshooting, and operator commands.

### `docs/security.md`

Records the threat model, controls, privacy assumptions, residual risks,
production boundaries, and security verification.

### `docs/code-quality.md`

Documents Ruff, mypy, pre-commit, test, and code-review practices.

### `docs/roadmap.md`

Summarizes completed phases, remaining portfolio work, future improvements, and
the definition of internship completion.

### `docs/research.md`

Records technical research and engineering choices supporting the prototype.

### `docs/images/dashboard-login.png`

Stores a documentation screenshot of the protected login experience.

## Generated and local-only directories

These are expected on a developer machine but are not source architecture:

- `.venv/` contains the local Python virtual environment.
- `frontend/node_modules/` contains installed npm packages.
- `frontend/dist/` contains compiled frontend output.
- `__pycache__/`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`, and
  `.pre-commit-cache/` contain tool caches.
- `.pnpm-store/` is a local package-manager cache and should not be documented as
  application code.
- `data/` and `*.db` contain local SQLite development data.
- `htmlcov/`, `.coverage`, and `coverage.xml` contain generated coverage output.
- `*.tsbuildinfo`, generated `vite.config.js`, and generated declaration files
  are TypeScript build artifacts.
- `.env` and `.env.postgres` contain real local configuration/secrets and must
  never be committed or copied into screenshots.
- PostgreSQL’s named Docker volume contains durable database data outside the
  repository tree.

## Planned desktop executable extension

The new executable requirement has been discussed but is not implemented yet.
If the supervisor accepts Electron, a future `desktop/` directory will wrap the
existing React interface in a Windows application, perform a real company-network
health check before login, display Retry/Quit when offline, and optionally start
with Windows.

That future layer will not replace FastAPI, PostgreSQL, Jira integration,
analytics, authorization, AI, or RAG. It will become a new presentation/runtime
shell above the current frontend:

```text
Windows executable (future Electron shell)
    ↓ contains
Current React interface
    ↓ calls
Current protected FastAPI backend
```

Until that work is explicitly approved and implemented, `frontend/` remains the
current presentation layer and no `desktop/` source directory should be claimed
as complete.

## Where to begin when reading the code

A new developer should read the repository in this order:

1. `README.md` for the purpose, status, and development history.
2. `KEEPUP.md` for the plain-language mental model.
3. `PROJECT_STRUCTURE.md` for file ownership and navigation.
4. `main.py` and `app/api/routes.py` for application composition.
5. `app/api/dependencies.py` for authentication and authorization boundaries.
6. `app/services/sync_service.py` for the Jira-to-database workflow.
7. `app/services/analytics_service.py` for deterministic project intelligence.
8. `app/services/rag_service.py` for retrieval and answer grounding.
9. `app/database/entities.py` and migrations for persistence.
10. `frontend/src/App.tsx` and `frontend/src/components/AppShell.tsx` for UI flow.
11. `tests/` to understand the expected behavior and safety guarantees.

The shortest accurate mental model is:

> Jira is the source of truth; synchronization creates shared local memory;
> deterministic services calculate facts; RAG retrieves relevant evidence; the
> local model explains only bounded evidence; FastAPI enforces access; and the
> interface presents the result without editing Jira.
