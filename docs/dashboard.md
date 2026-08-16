# Internship Demonstration Dashboard

## Purpose

The React dashboard turns the backend into a presentation-ready workspace for a
software team and an internship jury. It does not replace Jira or write changes
back to Jira. It presents synchronized Jira facts, deterministic analytics, and
grounded AI evidence in one controlled interface.

## Technology choices

- React provides reusable screens and components.
- TypeScript validates frontend contracts before release.
- Vite provides fast development and an optimized production build.
- TanStack Query manages API state, caching, loading, errors, and refreshes.
- Recharts visualizes delivery history, status distribution, and workload.
- Wouter provides lightweight client-side routing.
- Vitest and Testing Library verify behavior.
- Project-specific responsive CSS keeps the visual design deliberate and easy
  to explain during the internship defense.

Wouter was selected after the dependency audit found an advisory affecting the
React Router versions compatible with the local Node runtime. The application
needs only simple routes, so the smaller router keeps the design understandable.

## Implemented experience

- Protected login backed by FastAPI JWT authentication.
- Permission-aware navigation using exactly three interface roles: **Company
  Administrator**, **Project Administrator**, and **Team Member**.
- Product Owner, Scrum Master, Developer, and QA remain Scrum responsibilities;
  they do not create extra security roles.
- Stored-data-first overview metrics, history, status distribution, workload,
  sprint lists, and sprint membership.
- An actionable overview that highlights the active sprint, priority delivery
  signals, and recently updated work with direct links to the relevant view.
- Data-freshness indicator that checks the selected project every 15 seconds.
- Automatic refresh of open Team Member dashboards after an administrator sync,
- A shared **Updates available — sync required** state when Jira's latest issue
  is newer than the synchronized database snapshot.
- A project-administrator freshness check and expandable sync-run details showing
  issue keys, changed fields, before/after values, and inspected histories.
  with a short **Project data updated** confirmation.
- Human account display using optional first name, last name, and email, with a
  username fallback for older accounts.
- Searchable stored-issue explorer with status, priority, assignee, issue-type,
  overdue, blocked, stale, and unassigned filters.
- Clickable real Jira issue keys using a safe backend-provided Jira base URL.
- A sprint workspace that presents the active sprint first without hiding future
  planning or completed sprint history.
- Risk center for blocked, overdue, stale, unassigned, and concentrated work,
  including the reason each risk was raised, its severity, affected issues, and
  a practical next action.
- Team workload chart and per-person status breakdown.
- Navigable notifications that open the affected issues or administration view.
- Grounded AI results organized into answer, risks, actions, Jira sources,
  evidence, limitations, and optional technical details. Evidence relevance is
  described in human terms instead of presenting model similarity as certainty.
- In-page guidance explains which questions belong in Jira Knowledge and which
  signals belong in Delivery Risks. Sprint list/count questions bypass the
  models and return authoritative synchronized sprint facts.
- Jira Knowledge filters questions such as “Which issues have Medium priority?”
  by authoritative synchronized priority, status, assignee, or issue-type fields.
  Minor misspellings are tolerated, and unclear values produce a list of real
  available values rather than a guessed answer.
- RAG index status showing indexed issue/chunk counts and indexing timestamps.
- A cited-evidence panel that hides retrieved candidates rejected by the final
  grounded answer.
- Project administration split into Data operations, Sync history, and Access
  management so unrelated responsibilities are not mixed on one long screen.
- Safe demo mode with a persistent synthetic-workspace banner; it never requests
  company Jira data.
- Responsive layouts for compact desktop windows, tablets, and narrow screens.

## Security model

- Real login tokens live in browser session storage and are sent as Bearer
  tokens to FastAPI.
- A `401` response removes the token and returns the user to login.
- Team Members see only projects owned by their active Scrum teams.
- Project administrators can synchronize and index their explicitly assigned
  projects; company administrators can manage every project and access rule.
- Company administrators use the Access Management area to create Scrum teams,
  assign project ownership, manage memberships, and grant or revoke project
  administration.
- FastAPI remains the real authorization boundary; hidden UI is not security.
- The safe demo creates a synthetic viewer in the browser and intercepts every
  dashboard data request locally. No company data or secret is needed.
- The browser receives only the Jira base URL for issue links. Jira tokens,
  database passwords, and Ollama configuration remain server-side.

Production should replace local prototype accounts with company SSO/OIDC and a
reviewed session mechanism. The prototype must remain on trusted infrastructure
until deployment and security hardening are finished.

The backend role value remains `viewer` because it is an authorization contract.
The dashboard labels that role **Team Member** because it better describes a
developer, tester, Scrum Master, Product Owner, or other Scrum participant who
consumes shared intelligence without administering the data pipeline.

## Run locally

Start PostgreSQL, migrations, Ollama, and FastAPI from the repository root:

```powershell
docker compose up -d postgres
$env:DATABASE_URL = "postgresql+psycopg://jira_ai:YOUR_PASSWORD@localhost:5432/jira_ai"
python -m alembic upgrade head
python -m uvicorn main:app --reload
```

Start the dashboard in another terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open the URL printed by Vite, normally `http://127.0.0.1:5173`. Sign in with a
prototype account for real synchronized data, or choose **Explore safe demo** to
present synthetic data without exposing company information.

## Verify the dashboard

```powershell
cd frontend
npm test -- --run
npm run build
npm audit --omit=dev
```

Verified Phase 10 result:

- Four frontend unit tests passed.
- Strict TypeScript production compilation passed.
- The optimized route-split Vite build passed.
- Ruff and mypy passed for the backend additions.
- 110 backend tests passed; two optional PostgreSQL tests were skipped when their
  dedicated test URL was absent.
- A desktop browser walkthrough passed for login, safe demo, overview, risks,
  team workload, sprint detail, notifications, and grounded evidence display.
- The last successful production dependency audit reported zero vulnerabilities.
  The audit requires npm registry access and should be rerun before release.

## Demonstration sequence

1. Open login and explain that real accounts are backend-managed.
2. Select **Explore safe demo** when company Jira data cannot be shown.
3. Point out the data-freshness label and deterministic notification count.
4. Explain the overview metrics, status distribution, and workload chart.
5. Open Risk center and Team workload to show actionable delivery signals.
6. Open Sprints, select a sprint, and show its issues, scope, throughput, and
   carryover.
7. Ask a knowledge question and open the exact Jira information used as evidence.
8. With an administrator account, show synchronization progress, RAG-index
   health, and the audit trail.

## Honest limitations

- Notifications are in-application signals, not email, Teams, or mobile push.
- Synchronization is request-driven; a background worker and scheduler belong to
  the deployment phase.
- The safe demo is intentionally read-only and synthetic.
- Automated end-to-end browser tests remain a useful later addition; Phase 10
  browser verification was an interactive walkthrough.
- The dashboard has responsive styles, but a native mobile application and Jira
  mobile integration are outside the current prototype scope.

## Phase 10 decision

Phase 10 is complete. The dashboard is presentable and functionally connected to
the backend while preserving a safe way to demonstrate the system. Phase 11 can
now focus on reproducible container startup and deployment operations.

## Post-review role-aware guidance

The dashboard now derives an interface role from the authenticated company role
and the currently selected project's administration grants. The result is one
maintainable interface with permission-aware behavior rather than separate,
duplicated applications:

- **Company administrators** see every project, synchronization and indexing,
  plus company team and access management.
- **Project administrators** see synchronization and indexing only while an
  administered project is selected.
- **Team members** see only their authorized read-only analytics and AI views.

A role badge and reusable **What can I do?** guide explain the current role. The
guide opens automatically once per account and browser, and remains available
from the header afterward. Context messages reinforce that Jira is the source of
truth, issue edits happen in Jira, AI answers rely on synchronized evidence, and
an ordinary team member must ask a project administrator to synchronize when
updates are available. Hidden navigation improves usability, while backend
authorization remains the actual security boundary.
