"""API router modules (router + routes 통합)."""

from router.chat_router import router as chat_router
from router.health import router as health_router
from router.search import router as search_router

__all__ = ["chat_router", "health_router", "search_router"]
