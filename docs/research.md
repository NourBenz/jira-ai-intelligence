# Research and Technical References

The previous `research.pdf` was not a PDF; it was a short Markdown placeholder
with the wrong extension. This file replaces it with the references that support
the implemented architecture.

## Jira Cloud

- [Jira Cloud Platform REST API v3](https://developer.atlassian.com/cloud/jira/platform/rest/v3/)
- [Jira Software Cloud REST API](https://developer.atlassian.com/cloud/jira/software/rest/)
- [Atlassian Document Format](https://developer.atlassian.com/cloud/jira/platform/apis/document/structure/)
- [Jira Cloud basic authentication for scripts](https://developer.atlassian.com/cloud/jira/platform/basic-auth-for-rest-apis/)
- [Jira OAuth 2.0 authorization code grants](https://developer.atlassian.com/cloud/jira/platform/oauth-2-3lo-apps/)

The prototype uses Jira REST API v3 for platform data and Agile endpoints for
boards, sprints, and sprint issues. Jira descriptions and comment bodies may use
Atlassian Document Format and are converted to text before embedding.

## FastAPI and validation

- [FastAPI documentation](https://fastapi.tiangolo.com/)
- [FastAPI dependency injection](https://fastapi.tiangolo.com/tutorial/dependencies/)
- [FastAPI metadata and documentation URLs](https://fastapi.tiangolo.com/tutorial/metadata/)
- [Pydantic documentation](https://docs.pydantic.dev/latest/)
- [pydantic-settings documentation](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)

Dependency injection is used to replace Jira and RAG services during offline API
tests. Pydantic validates settings, request bodies, and response contracts.

## Persistence

- [SQLAlchemy 2.0 documentation](https://docs.sqlalchemy.org/en/20/)
- [Alembic documentation](https://alembic.sqlalchemy.org/)
- [PostgreSQL documentation](https://www.postgresql.org/docs/)
- [psycopg documentation](https://www.psycopg.org/psycopg3/docs/)
- [pgvector repository and usage](https://github.com/pgvector/pgvector)

SQLAlchemy maps the relational model, Alembic versions schema changes, psycopg
connects Python to PostgreSQL, and pgvector stores and compares embeddings.

## Local AI and embeddings

- [Ollama API documentation](https://docs.ollama.com/api/introduction)
- [Ollama embedding endpoint](https://docs.ollama.com/api/embed)
- [Ollama model library](https://ollama.com/library)
- [Nomic Embed Text model card](https://huggingface.co/nomic-ai/nomic-embed-text-v1.5)

The Nomic model card requires task prefixes for retrieval. Indexed documents use
`search_document:` and questions use `search_query:`. This requirement was found
during live retrieval evaluation and is protected by automated tests.

## Testing

- [pytest documentation](https://docs.pytest.org/)
- [FastAPI testing](https://fastapi.tiangolo.com/tutorial/testing/)

Tests use dependency overrides, fake Jira services, fake model responses,
monkeypatching, temporary SQLite databases, and opt-in PostgreSQL checks.

## Engineering concepts used in the report

### Deterministic analytics

Mathematical facts are computed in normal code so identical evidence produces
identical results. AI is not trusted to calculate completion rates or risk
counts.

### Idempotent synchronization

Repeated synchronization updates the same logical entities instead of producing
duplicates. Stable Jira identifiers and relational uniqueness constraints support
this property.

### Retrieval-Augmented Generation

RAG retrieves domain evidence before generation. This prototype embeds stored
Jira text, retrieves project-scoped candidates, and permits only citations from
those candidates.

### Recall@K

Recall@K reports whether an expected relevant issue appears inside the top K
retrieved results.

### Mean Reciprocal Rank

For each query, reciprocal rank is one divided by the first relevant result's
rank. Mean Reciprocal Rank averages that value across evaluation cases.

### Lead time and cycle time

Lead time measures creation to resolution. Cycle time measures active-work start
to resolution. Jira changelogs are required to infer active-work start.

### Throughput and velocity

Throughput counts completed issues. Velocity uses completed story points when
estimates exist. The prototype does not invent missing estimates.

## Verified project evidence

- Python 3.12.6.
- PostgreSQL 17 with pgvector 0.8.2.
- Alembic head `20260723_05`.
- Local `llama3.2` answer model.
- Local `nomic-embed-text` embedding model.
- 110 passing tests with zero skips when PostgreSQL tests are enabled.
- 83.56% combined statement and branch coverage with an 80% gate.
- Five-case live retrieval Recall@K `1.0`.
- Five-case Mean Reciprocal Rank `0.8333`.

## Research limitations

- The evaluation dataset is intentionally small and project-specific.
- Current T1 data contains short summaries and no real comments.
- The prototype has not compared multiple embedding models under identical
  hardware and evaluation conditions.
- Security and deployment research remains for later phases.
- Product claims should be limited to observed test and live-verification
  evidence.
