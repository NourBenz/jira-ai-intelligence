"""Authenticated business-route composition."""

from fastapi import APIRouter, Depends

from app.api.access_routes import router as access_router
from app.api.analytics_routes import router as analytics_router
from app.api.dependencies import require_viewer
from app.api.intelligence_routes import router as intelligence_router
from app.api.jira_routes import router as jira_router
from app.api.stored_routes import router as stored_router
from app.api.sync_routes import router as sync_router

router = APIRouter(dependencies=[Depends(require_viewer)])
router.include_router(access_router)
router.include_router(intelligence_router)
router.include_router(stored_router)
router.include_router(sync_router)
router.include_router(jira_router)
router.include_router(analytics_router)
