"""AI and RAG endpoints."""

from fastapi import APIRouter, Depends, HTTPException

from app.ai.ollama_client import OllamaClient
from app.api.dependencies import (
    DatabaseSessionDependency,
    ProjectAccessDependency,
    ProjectKeyPath,
    RAGServiceDependency,
    limit_admin_operation,
    limit_ai_request,
    require_project_administrator,
)
from app.core.config import get_settings
from app.database.repositories import RAGRepository
from app.schemas.ai import ProjectAIResponse, ProjectQuestionRequest
from app.schemas.rag import (
    RAGAnswerRequest,
    RAGAnswerResponse,
    RAGIndexResponse,
    RAGIndexStatusResponse,
    RAGSearchRequest,
    RAGSearchResponse,
)
from app.services.ai_service import AIService
from app.services.evidence_service import EvidenceService
from app.services.stored_data_service import StoredDataService

router = APIRouter(tags=["intelligence"])


@router.get(
    "/rag/projects/{project_key}/status",
    response_model=RAGIndexStatusResponse,
)
def get_project_knowledge_status(
    project_key: ProjectKeyPath,
    _access: ProjectAccessDependency,
    database: DatabaseSessionDependency,
):
    return RAGRepository(database).index_status(project_key)


@router.post(
    "/rag/projects/{project_key}/index",
    response_model=RAGIndexResponse,
    dependencies=[Depends(require_project_administrator), Depends(limit_admin_operation)],
)
def index_project_knowledge(
    project_key: ProjectKeyPath,
    rag_service: RAGServiceDependency,
):
    result = rag_service.index_project(project_key)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"No stored issues found for project '{project_key}'.",
        )
    return result


@router.post(
    "/rag/projects/{project_key}/search",
    response_model=RAGSearchResponse,
    dependencies=[Depends(limit_ai_request)],
)
def search_project_knowledge(
    project_key: ProjectKeyPath,
    _access: ProjectAccessDependency,
    request: RAGSearchRequest,
    rag_service: RAGServiceDependency,
):
    return rag_service.search(project_key, request.query, request.top_k)


@router.post(
    "/rag/projects/{project_key}/ask",
    response_model=RAGAnswerResponse,
    dependencies=[Depends(limit_ai_request)],
)
def ask_project_knowledge(
    project_key: ProjectKeyPath,
    _access: ProjectAccessDependency,
    request: RAGAnswerRequest,
    rag_service: RAGServiceDependency,
):
    result = rag_service.ask(project_key, request.question)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"No indexed evidence found for project '{project_key}'.",
        )
    return result


@router.post(
    "/ai/projects/{project_key}/ask",
    response_model=ProjectAIResponse,
    dependencies=[Depends(limit_ai_request)],
)
def ask_project_ai(
    project_key: ProjectKeyPath,
    _access: ProjectAccessDependency,
    request: ProjectQuestionRequest,
    database: DatabaseSessionDependency,
):
    settings = get_settings()
    stored = StoredDataService(database)
    service = AIService(
        EvidenceService(stored),
        OllamaClient(settings.ollama_base_url, settings.ollama_model),
    )
    result = service.ask_project(project_key, request.question)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"No stored evidence found for project '{project_key}'.",
        )
    return result
