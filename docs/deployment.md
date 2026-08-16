# Local deployment guide

This guide packages Jira AI Intelligence as a private, reproducible deployment
for internship demonstrations and internal evaluation. It does not publish Jira
data to the internet. All published ports bind to `127.0.0.1`, and Ollama keeps
generation and embeddings on the host machine.

## What runs

- `postgres` runs PostgreSQL 17 with pgvector and retains data in a named volume.
- `migrate` runs Alembic once and must finish successfully before the API starts.
- `backend` runs FastAPI with Uvicorn as a non-root Linux user.
- `frontend` serves the compiled React application through unprivileged Nginx.
- Ollama remains outside Compose and is reached through `host.docker.internal`.

The dashboard reverse-proxies API calls to FastAPI. This gives the browser one
origin and keeps internal container hostnames out of frontend code.

The Nginx entry page is served with a no-cache policy so a browser discovers a
new hashed dashboard bundle after deployment. Versioned assets are immutable,
and an obsolete asset path returns `404` instead of the HTML application shell.

The gateway and API emit defensive browser headers. API responses use
`Cache-Control: no-store`; the dashboard entry page has a restrictive content
security policy; and POST, PUT, and PATCH bodies are limited to 1 MiB by default.
Set `MAX_REQUEST_BODY_BYTES` in `.env` only when a documented endpoint genuinely
needs a larger payload. See [security.md](security.md) for the threat model.

## First-time configuration

Install Docker Desktop and Ollama, then make sure these local models exist:

```powershell
ollama pull llama3.2
ollama pull nomic-embed-text
```

Create the private configuration files:

```powershell
Copy-Item .env.example .env
Copy-Item .env.postgres.example .env.postgres
```

Replace every example credential. The Jira token and JWT secret belong in
`.env`; the PostgreSQL password belongs in `.env.postgres`. Never commit either
file. `DATABASE_URL` may retain its local SQLite value because the container
entrypoint safely builds the PostgreSQL URL from the separate database fields.

## Start the application

Make sure Ollama is running, then execute:

```powershell
docker compose up -d --build
docker compose ps
```

Open the dashboard at `http://127.0.0.1:3000`. Swagger is available through the
same gateway at `http://127.0.0.1:3000/docs`. Direct local API access remains at
`http://127.0.0.1:8000` for Postman.

Create the first prototype users through the container entrypoint so they
receive the same PostgreSQL configuration as the API:

```powershell
docker compose run --rm backend python -m scripts.create_user admin-demo --role admin --first-name Nour --last-name Admin --email nour.admin@example.com
docker compose run --rm backend python -m scripts.create_user viewer-demo --role viewer --first-name Nour --last-name Viewer --email nour.viewer@example.com
```

Replace the example profile details with the employee's real internal details.
The password prompt remains hidden. Re-running the command updates an existing
account, which is useful for assigning profile details to accounts created
before migration `20260803_06`.

## Operational checks

```powershell
docker compose ps
docker compose logs --tail 100 backend
docker compose logs --tail 100 migrate
Invoke-RestMethod http://127.0.0.1:8000/health
Invoke-RestMethod http://127.0.0.1:8000/ready
Invoke-RestMethod http://localhost:11434/api/version
```

The process health endpoint proves FastAPI is running. The readiness endpoint
proves required configuration is valid. Compose separately waits for
PostgreSQL, requires the migration job to succeed, and checks both the API and
web server before reporting them healthy.

## Updating the deployment

```powershell
docker compose build backend frontend
docker compose up -d
docker compose ps
```

Alembic runs before every backend start. Migrations are idempotent, so an
already-current database is left unchanged.

## Backup and restore

Create a PostgreSQL custom-format backup:

```powershell
New-Item -ItemType Directory -Force backups
docker compose exec postgres pg_dump -U jira_ai -d jira_ai -Fc -f /tmp/jira_ai.dump
docker compose cp postgres:/tmp/jira_ai.dump ./backups/jira_ai.dump
```

To restore into an intentionally selected database, stop application writes,
copy the backup into the container, and run `pg_restore`:

```powershell
docker compose stop backend
docker compose cp ./backups/jira_ai.dump postgres:/tmp/jira_ai.dump
docker compose exec postgres pg_restore -U jira_ai -d jira_ai --clean --if-exists /tmp/jira_ai.dump
docker compose up -d backend frontend
```

Restoration is destructive to the selected database. Confirm the target and
retain another backup before running it.

## Rollback strategy

Application rollback means switching to a known-good Git tag or commit and
rebuilding the two application images. Database migrations should normally be
repaired with a new forward migration. Only use `alembic downgrade` after
confirming that the migration is reversible and a backup exists.

For a real company deployment, CI should produce immutable, versioned images.
The platform can then point back to a previous image tag without rebuilding.

## Recommended target

The safe internship target is Docker Desktop on a company-controlled laptop or
an internal Linux virtual machine behind company access controls. A future
company deployment should add TLS, SSO/OIDC, managed secrets, managed
PostgreSQL backups, centralized logs, shared rate limiting, and monitoring
before the service is exposed to a wider network.

Public student hosting is deliberately not recommended because Jira issue text,
comments, identities, tokens, and generated answers may contain company data.

The Windows client is deployed separately from these central services. See
[desktop.md](desktop.md) for installer creation, startup behavior, the offline
connection gate, and IT-managed company URL configuration.
