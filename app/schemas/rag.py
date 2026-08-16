"""Validated request and response contracts for semantic retrieval."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class RAGIndexResponse(BaseModel):
    project_key: str
    issues_processed: int
    chunks_indexed: int
    embedding_model: str


class RAGIndexStatusResponse(BaseModel):
    project_key: str
    issues_indexed: int
    chunks_indexed: int
    last_indexed_at: datetime | None
    latest_source_update: datetime | None


class RAGSearchRequest(BaseModel):
    query: str = Field(min_length=3, max_length=1000)
    top_k: int = Field(default=5, ge=1, le=20)


class RAGSearchResultSchema(BaseModel):
    chunk_id: str
    text: str
    metadata: dict[str, Any]
    similarity: float


class RAGSearchResponse(BaseModel):
    project_key: str
    query: str
    results: list[RAGSearchResultSchema]
    returned: int
    embedding_model: str


class RAGAnswerRequest(BaseModel):
    question: str = Field(min_length=3, max_length=1000)


class RAGAnswerContent(BaseModel):
    answer: str
    source_issue_keys: list[str]
    limitations: list[str]


class RAGAnswerResponse(RAGAnswerContent):
    project_key: str
    model: str
    retrieved_chunks: int
    grounded: bool = True
    evidence: list[RAGSearchResultSchema] = Field(default_factory=list)
