# Product and Engineering Roadmap

## Current status

Phases 1 through 12 are implemented and verified. The presentation dashboard,
safe synthetic demo, browser walkthrough, supporting documentation, and private
container deployment are complete. The post-review project/team authorization
hardening is complete; Phase 13 Git and portfolio quality is next.

The latest offline baseline is 156 passed tests with two PostgreSQL-only tests
skipped when their dedicated database URL is absent. The verified PostgreSQL
migration head is `20260805_08`; the five-case RAG evaluation achieved Recall@K
`1.0` and Mean Reciprocal Rank `0.8333`. Current combined coverage is 83.85%,
above the required 80% gate.

## Completed phases

### Phase 1 — Backend stabilization and Jira integration

- Typed environment configuration.
- Safe Jira client and error handling.
- Projects, boards, sprints, issues, users, comments, and changelogs.
- Correct offset and token pagination.
- Ticket cleaning and Jira status-category support.
- Dependency injection, safe logging, `/health`, and `/ready`.
- Meaningful offline and live tests.

### Phase 2 — Deterministic analytics

- Project overview and distributions.
- Workload, overdue, stale, blocked, and unassigned metrics.
- Weekly created and completed trends.
- Lead time and cycle time.
- Sprint completion, throughput, velocity, carryover, and scope change.
- Live verification against T1 and sprints 34, 68, and 69.

### Phase 3 — Safe filtering and search

- Validated filters and allowlisted sorting.
- Safe JQL construction.
- Cursor pagination.
- Rejection of malformed and injection-like input before Jira calls.

### Phase 4 — Persistence and synchronization

- SQLAlchemy entities and Alembic migrations.
- SQLite and PostgreSQL support.
- Idempotent full and incremental synchronization.
- Stored issues, changelogs, comments, sprints, and memberships.
- Observable synchronization runs.
- Database-backed analytics without Jira network calls.
- Caching deliberately deferred until profiling justifies it.

### Phase 5 — Grounded AI assistant

- Local Ollama and `llama3.2`.
- Structured JSON-schema responses.
- Deterministic risk signals and recommendations.
- Citation allowlisting and prompt-injection isolation.
- Explicit evidence limitations.

### Phase 6 — RAG and semantic search

- Deterministic source-aware chunking.
- Local `nomic-embed-text` embeddings.
- PostgreSQL pgvector persistence.
- Project-scoped semantic retrieval.
- Grounded top-ten answer generation.
- Persisted Jira comment support.
- Repeatable Recall@K and MRR evaluation.

## Later completed phases

### Phase 7 — Authentication and authorization

- Local JWT authentication with Argon2 password hashing is implemented.
- Viewer and administrator role boundaries are implemented.
- Business routes require authentication.
- Synchronization and RAG indexing require administrator access.
- Restrictive configurable CORS and process-local rate limiting are implemented.
- Future company SSO/OIDC replacement is documented.
- PostgreSQL migration and live viewer/admin Postman verification passed.
- Human profile fields are available while older username-only users remain
  compatible.
- The UI calls the read-only `viewer` role **Team Member** without changing the
  authorization value.

### Phase 8 — Testing completeness

- Statement and branch coverage are measured with `pytest-cov`.
- An 80% minimum coverage gate is configured.
- Deterministic AI evidence and security negative paths are covered.
- PostgreSQL and pgvector integration tests pass.
- The obsolete sprint-health placeholder was removed.
- Final result: 110 passed, zero skipped, 83.56% branch coverage.

### Phase 9 — Code quality

- `pyproject.toml` configures Ruff and mypy.
- Local pre-commit hooks run Ruff lint, Ruff format checking, and mypy.
- Confirmed unreferenced placeholder scaffolding was deleted.
- All current Ruff and mypy findings were resolved.
- The former 622-line API module was split into intelligence, stored-data,
  synchronization, direct-Jira, and analytics routers.
- All 38 API paths and authorization dependencies were preserved.
- Regression coverage remains above the 80% gate; the current full run reports
  83.85%.

## Completed presentation phase

### Phase 10 — Dashboard and documentation

- Keep README, KEEPUP, and docs synchronized.
- Build a responsive, authenticated internship demonstration dashboard. Done.
- Present overview analytics, issues, sprints, grounded intelligence, and
  administrator synchronization. Done.
- Verify strict TypeScript compilation, unit tests, production build, and
  production dependency audit. Done.
- Data freshness, Jira links, sprint detail, risk center, team workload,
  deterministic notifications, visible AI evidence, RAG-index status, sync
  progress and a safe synthetic demo are implemented. CSV/PDF controls were
  later removed to keep the read-only workspace focused and uncluttered.
- The complete backend and frontend test/build gates pass.
- Desktop browser verification covers the protected login and all main viewer
  demonstration flows.
- Usage, security boundaries, limitations, and the demonstration sequence are
  documented in `docs/dashboard.md`.
- Open dashboards detect a new completed administrator sync within about 15
  seconds, refresh selected-project data, and notify the user.

## Completed deployment phase

### Phase 11 — Docker and deployment

- FastAPI and the React/Nginx dashboard have separate reproducible images.
- Compose coordinates PostgreSQL/pgvector, one-time migrations, the backend,
  and the frontend with explicit health and startup dependencies.
- Container configuration safely constructs the database URL from private
  PostgreSQL fields and reaches host-managed Ollama.
- All published ports bind to localhost for a company-safe prototype.
- Deployment, update, backup, restore, and rollback procedures are documented.
- The complete local stack was built and reached healthy state.

### Phase 12 — Security hardening

- Completed secrets and dependency audits with no known runtime vulnerabilities.
- Added API/dashboard security headers, no-store caching, and measured body limits.
- Reviewed logging, credentials, personal data, and stored Jira sensitivity.
- Added abuse, prompt-injection, and authorization regression tests.
- Added one-company Scrum-team authorization: one owning team per project,
  multi-team user membership, company administrators, and explicit per-project
  administrators.
- Restricted project discovery and every project, sprint, issue, analytics,
  synchronization, AI, and RAG route to the caller's authorized project scope.
- Added company-admin dashboard controls for teams, memberships, project
  ownership, and project-administrator grants.
- Escaped project values before direct Jira JQL construction.
- Documented the threat model, privacy limits, and residual production risks.

## Remaining repository phases

### Phase 13 — Git and portfolio quality

- Clean repository history and ignored artifacts.
- Add clear commit and branch conventions.
- Prepare internship report evidence.
- Prepare presentation, screenshots, and demo script.
- Perform final prototype and portfolio review.

## Future product improvements

These are not required to claim the current phases are complete:

- Scheduled background synchronization.
- Hybrid keyword and vector retrieval.
- Reranking for short Jira summaries.
- Larger evaluation datasets from real team questions.
- Configurable risk policies.
- True multi-company tenancy. Multi-project authorization inside one company is
  already implemented.
- Deeper Jira-integrated UI features beyond the implemented web dashboard.
- Notifications and scheduled reports.
- Model-provider adapters beyond Ollama.

## Definition of internship completion

The internship prototype is complete when the remaining engineering phases are
verified and the student can demonstrate:

- Safe Jira integration.
- Reliable deterministic analytics.
- Persistent and observable synchronization.
- Grounded local AI and RAG.
- Security boundaries.
- Reproducible tests and deployment.
- Clear report, diagrams, documentation, and live demonstration.
