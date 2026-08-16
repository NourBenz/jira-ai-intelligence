# Code Quality Guide

## Why this work exists

Code-quality tooling turns team conventions into repeatable checks. It catches
incorrect imports, suspicious Python constructs, inconsistent formatting, and
type mismatches before they become runtime defects or review distractions.

## Tools

- Ruff formats Python and performs fast static linting.
- Mypy checks that values passed between modules match their declared types.
- Pre-commit runs these checks before a Git commit when installed.
- Pytest protects behavior with unit, API, database, security, AI, and RAG tests.
- pytest-cov enforces the 80% statement-and-branch coverage gate.

## Configuration

`pyproject.toml` targets Python 3.12 and contains the Ruff and mypy policies.
`.pre-commit-config.yaml` defines local hooks and does not download third-party
hook repositories. `.coveragerc` contains the coverage scope and threshold.

Alembic migration scripts are excluded from automatic Ruff formatting because
migrations are historical database records and should not be mechanically
rewritten after deployment.

## Commands

Install the project dependencies:

```powershell
python -m pip install -r requirements.txt
```

Run linting and verify formatting:

```powershell
python -m ruff check app tests main.py scripts
python -m ruff format --check app tests main.py scripts
```

Apply safe automatic formatting and lint fixes:

```powershell
python -m ruff check --fix app tests main.py scripts
python -m ruff format app tests main.py scripts
```

Run static type checking:

```powershell
python -m mypy app main.py scripts
```

Enable and run the commit hooks:

```powershell
python -m pre_commit install
python -m pre_commit run --all-files
```

Run the regression and coverage gates:

```powershell
python -m pytest -q
python -m pytest --cov=app --cov=main --cov-report=term-missing -q
```

The PostgreSQL tests additionally require `POSTGRES_TEST_DATABASE_URL` to point
to the isolated local test database. Without it, those two tests skip by design.

## Cleanup decisions

The removed files were empty or pass-only placeholders with no imports and no
runtime responsibility. Keeping such files would falsely imply that features
were implemented and would lower meaningful coverage. Implemented services,
schemas, migrations, tests, and package initializers were retained.

The cleanup also made narrow type-safety improvements. Nullable Jira timestamps
are narrowed before date operations, RAG search results are constructed as their
declared Pydantic schema, database engine keyword options have an explicit type,
and a missing just-created synchronization run now raises an internal invariant
error instead of being dereferenced blindly.

## Current result

- Ruff lint passes with no findings.
- Ruff formatting passes.
- Mypy reports no issues across 52 source files.
- The offline test run passes 146 tests; two PostgreSQL tests skip without their
  opt-in database variable.
- The frontend passes 12 Vitest tests and a strict TypeScript/Vite production
  build.
- The Electron client passes four runtime-configuration tests and syntax checks
  for its main, preload, retry, configuration, and Forge files.
- Python runtime, frontend npm, and desktop npm dependency audits report no
  known vulnerabilities as of 2026-08-12.
- The PostgreSQL and pgvector tests pass separately against local Compose.
- Total statement and branch coverage is 83.85%, above the 80% gate.

The former 622-line route module is now divided into intelligence, stored-data,
synchronization, direct-Jira, and analytics routers. The composition router
retains the global viewer dependency, privileged operations retain their admin
dependency, and all 38 API paths are preserved.
