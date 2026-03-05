"""KOICA 도메인 라우터 - soccer의 여러 라우터를 묶는 것과 동일한 역할.

- chat_router: KOICA 채팅 API (/api/v1/koica/chat)
- 추후 project_router, qa_router 등 추가 가능
"""

from fastapi import APIRouter

from app.api.v1.koica.chat_router import router as koica_chat_router
from app.api.v1.koica.report_router import router as koica_report_router

router = APIRouter(prefix="/api/v1/koica", tags=["koica"])

router.include_router(koica_chat_router)
router.include_router(koica_report_router)
