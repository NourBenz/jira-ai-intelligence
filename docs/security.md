# Security and Privacy Review

This document records the Phase 12 threat model for the private Jira AI
Intelligence prototype. It covers the browser, Nginx, FastAPI,
PostgreSQL/pgvector, Jira Cloud, and host-managed Ollama.

## Security objective

Only authenticated company team members may read synchronized Jira projects
owned by one of their active Scrum teams. Company administrators may manage all
projects; explicit project administrators may synchronize and index only their
assigned projects. Credentials,
personal data, and issue content must not leak through source control, logs,
browser caches, model hallucinations, or cross-project retrieval.

This is a hardened internship prototype, not a claim of production readiness.

## Protected assets

- Jira API token and account email.
- JWT signing secret and PostgreSQL credentials.
- Local account password hashes and identity profiles.
- Jira issues, comments, changelogs, sprint membership, and analytics.
- Vector embeddings, retrieved evidence, and browser authentication tokens.

## Trust boundaries

- The browser sends bearer tokens through the same-origin Nginx gateway.
- Nginx serves React and proxies `/api` to FastAPI.
- FastAPI validates identity, role, input, rate limits, and project scope.
- PostgreSQL stores synchronized records, users, and vectors.
- Jira Cloud is the authoritative external source.
- Ollama receives bounded evidence locally for embeddings and answers.

Jira text and user questions are untrusted even when they originate inside the
company. They may contain malformed data or prompt-injection instructions.

## Implemented controls

### Credentials and authentication

- `.env` and `.env.postgres` are ignored and are not tracked by Git.
- Example environment files contain placeholders only.
- Pydantic secret fields prevent accidental representation of tokens.
- Passwords use Argon2 hashes and are never stored in plaintext.
- Signed JWTs expire and are rejected when malformed, expired, disabled, or
  inconsistent with the user's current database role.
- Authentication failures use one generic response to reduce account discovery.

### Authorization and data isolation

- Every Jira project has at most one owning Scrum team; a team may own multiple
  projects and a user may actively belong to multiple teams.
- Business routes require active membership in the owning team, an explicit
  project-administrator assignment, or the company-administrator role.
- Synchronization and RAG indexing require a company administrator or an active
  administrator assignment for that specific project.
- Project lists contain only synchronized projects the current user may access;
  typing or guessing a Jira key does not grant access.
- Sprint and issue routes resolve their stored parent project before access.
- Team, membership, ownership, and project-admin changes are company-admin-only.
- Browser visibility is not trusted as authorization; FastAPI enforces roles.
- Stored retrieval and pgvector search are scoped by project key.
- AI citations are filtered against issue keys in retrieved evidence.

### Input, abuse, and model safety

- Pydantic validates query and body fields.
- Jira search options are allow-listed before JQL construction.
- POST, PUT, and PATCH bodies are limited to 1 MiB by default. Actual received
  bytes are measured, including requests without Content-Length.
- Login, AI, and administrator operations are rate-limited.
- Questions and retrieved Jira content are explicitly treated as untrusted data.
- Deterministic routers answer structured facts without calling the model.
- Invented citations are removed and unsupported answers fail closed.

### Browser, transport, and caching

- CORS accepts only explicitly configured origins without credentials.
- API responses use `Cache-Control: no-store`.
- FastAPI and Nginx emit content-type, frame, referrer, permissions, and
  same-origin resource-policy protections.
- The dashboard has a restrictive content security policy.
- HSTS is emitted by FastAPI when reached over HTTPS.
- Container ports bind to localhost and application containers run as non-root.

### Logging and dependency controls

- Logs record resource paths, status, duration, and safe error categories, not
  credentials or Jira response bodies.
- Connection and model errors are sanitized.
- `pip-audit`, `npm audit`, Bandit, Ruff, mypy, and regression tests form a
  repeatable security gate.

## Main threat scenarios

### Stolen or guessed credentials

Argon2, generic failures, login rate limiting, expiring JWTs, and disabled-user
checks reduce impact. Production still needs company SSO, MFA, revocation, and
central identity lifecycle management.

### Team member attempts an administrator action

FastAPI returns `403` before synchronization or indexing unless that user is an
explicit administrator for the requested project. Regression tests cover
cross-team reads, project-admin boundaries, and membership revocation.

### Cross-site access or cached Jira data

Explicit CORS, same-origin proxying, defensive headers, and no-store responses
reduce browser leakage. Production requires TLS at the ingress.

### Oversized or repeated expensive requests

The API rejects oversized bodies and rate-limits expensive routes. The limiter is
process-local; multi-instance production needs Redis or an API gateway plus
background jobs for long synchronization and indexing work.

### JQL or prompt injection

JQL fields and sorts are validated before query construction. Questions and Jira
text cannot override the RAG policy. Retrieved keys are scoped and citations are
verified after generation. These controls limit, but do not eliminate, risk.

### Database or backup disclosure

The database contains company Jira content and personal identifiers. Localhost
binding limits network exposure, but production needs encrypted storage and
backups, retention rules, access logging, and key rotation.

## Privacy limits

The prototype stores names, email addresses, assignees, reporters, issue text,
comments, and work-history metadata. Only fields required by the prototype should
be synchronized. Demo mode must be used for public internship presentations.
Real company data must not appear in screenshots, reports, source control, or
external AI services.

## Residual production risks

- Local accounts do not provide SSO, MFA, password reset, or central offboarding.
- Team and project assignments are locally administered rather than synchronized
  from Jira groups or a company identity provider.
- JWTs in session storage remain exposed if arbitrary script execution occurs.
- Rate limits are process-local and reset when the API restarts.
- Local HTTP is acceptable only on the loopback demonstration environment.
- There is no central audit trail, SIEM integration, alerting, or secret rotation.
- Synchronization is synchronous and can occupy a worker for an extended time.
- Ollama availability and model quality remain local dependencies.

## Required production controls

- Company OIDC/SSO with MFA and group-to-role mapping.
- TLS, managed certificates, and secure ingress policy.
- A secret manager with credential rotation.
- Automatic Jira-group or identity-provider synchronization plus formal access
  reviews and auditable grant/revoke events.
- Central rate limiting, job queues, audit logging, monitoring, and alerts.
- Encrypted PostgreSQL storage and backups with restore exercises.
- Dependency scanning and the complete quality gate in CI.
- Privacy approval for Jira fields, retention, model use, and employee access.

## Repeatable verification

```powershell
python -m pip_audit -r requirements-runtime.txt
python -m bandit -r app main.py scripts -q
npm --prefix frontend audit --omit=dev
python -m pytest -q
python -m ruff check .
python -m mypy app main.py scripts
npm --prefix frontend test
npm --prefix frontend run build
```

The Phase 12 review found no known Python runtime vulnerabilities, no npm
production vulnerabilities, no unaddressed Bandit findings, and no private
environment files tracked by Git.
