FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements-runtime.txt ./
RUN python -m pip install --upgrade pip \
    && python -m pip install -r requirements-runtime.txt

RUN addgroup --system jira-ai \
    && adduser --system --ingroup jira-ai --home /app jira-ai

COPY --chown=jira-ai:jira-ai alembic.ini main.py ./
COPY --chown=jira-ai:jira-ai app ./app
COPY --chown=jira-ai:jira-ai migrations ./migrations
COPY --chown=jira-ai:jira-ai scripts ./scripts

USER jira-ai

EXPOSE 8000

ENTRYPOINT ["python", "-m", "scripts.docker_entrypoint"]
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips=*"]
