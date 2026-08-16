"""Deterministic text chunking for project-scoped RAG evidence."""

from collections.abc import Iterable
from dataclasses import asdict, dataclass
from datetime import datetime
from hashlib import sha256
from typing import Any

from app.models.ticket import Ticket


@dataclass(frozen=True)
class RAGChunk:
    """A traceable piece of Jira text ready for embedding."""

    id: str
    text: str
    metadata: dict[str, Any]

    def model_dump(self) -> dict[str, Any]:
        return asdict(self)


def chunk_document(
    document: str,
    chunk_size: int = 1000,
    overlap: int = 100,
) -> list[str]:
    """Split normalized text deterministically with bounded overlap."""
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be between zero and chunk_size")

    text = " ".join(document.split())
    if not text:
        return []

    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        if end < len(text):
            boundary = max(
                text.rfind(". ", start, end),
                text.rfind("? ", start, end),
                text.rfind("! ", start, end),
                text.rfind(" ", start, end),
            )
            if boundary > start + (chunk_size // 2):
                end = boundary + 1

        chunk = text[start:end].strip()
        if chunk and (not chunks or chunk != chunks[-1]):
            chunks.append(chunk)
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)

    return chunks


def chunk_issues(
    issues: Iterable[Ticket],
    project_key: str,
    comments_by_issue: dict[str, list[dict[str, Any]]] | None = None,
    chunk_size: int = 1000,
    overlap: int | None = None,
) -> list[RAGChunk]:
    """Create source-aware chunks from Jira issues and persisted comments."""
    effective_overlap = min(100, max(chunk_size // 10, 0)) if overlap is None else overlap
    chunks: list[RAGChunk] = []
    for issue in issues:
        sources = [
            {
                "content_type": "summary",
                "source_id": issue.key,
                "text": issue.summary or "",
                "updated_at": issue.updated,
                "author": None,
            },
            {
                "content_type": "description",
                "source_id": issue.key,
                "text": _description_text(issue.description),
                "updated_at": issue.updated,
                "author": None,
            },
        ]
        for comment in (comments_by_issue or {}).get(issue.key, []):
            body = _description_text(comment.get("body"))
            author = comment.get("author")
            sources.append(
                {
                    "content_type": "comment",
                    "source_id": str(comment.get("id") or "unknown"),
                    "text": f"Comment by {author}: {body}" if author else body,
                    "updated_at": comment.get("updated") or comment.get("created"),
                    "author": author,
                }
            )

        for source in sources:
            content_type = str(source["content_type"])
            source_id = str(source["source_id"])
            for index, text in enumerate(
                chunk_document(str(source["text"]), chunk_size, effective_overlap)
            ):
                source_identity = (
                    f"{project_key}|{issue.key}|{content_type}|{source_id}|{index}|{text}"
                )
                updated_at = source["updated_at"]
                chunks.append(
                    RAGChunk(
                        id=sha256(source_identity.encode("utf-8")).hexdigest(),
                        text=text,
                        metadata={
                            "project_key": project_key,
                            "issue_key": issue.key,
                            "content_type": content_type,
                            "source_id": source_id,
                            "chunk_index": index,
                            "source_updated_at": (
                                updated_at.isoformat()
                                if isinstance(updated_at, datetime)
                                else updated_at
                            ),
                            "author": source["author"],
                        },
                    )
                )
    return chunks


def intelligent_split(text: str) -> list[str]:
    """Compatibility wrapper using the default deterministic chunking policy."""
    return chunk_document(text)


def _description_text(value: dict[str, Any] | str | None) -> str:
    if isinstance(value, str):
        return value
    if not isinstance(value, dict):
        return ""

    collected: list[str] = []

    def visit(node: Any) -> None:
        if isinstance(node, dict):
            if isinstance(node.get("text"), str):
                collected.append(node["text"])
            for child in node.get("content", []):
                visit(child)
        elif isinstance(node, list):
            for child in node:
                visit(child)

    visit(value)
    return " ".join(collected)
