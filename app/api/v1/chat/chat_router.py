"""Chat 라우터 - ChatOrchestrator 기반 통합 챗봇

우선순위(오케스트레이터 내부에서 결정):
1) QuestionClassifier로 도메인 분류 (term / koica / general)
2) Term / Koica / General 오케스트레이터로 라우팅
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.domain.chat.bases.chat_result import ChatResult
from app.domain.chat.orchestrators.chat_orchestrator import ChatOrchestrator

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])

# 전역 오케스트레이터 인스턴스 (애플리케이션 시작 시 초기화)
_chat_orchestrator: Optional[ChatOrchestrator] = None


def get_chat_orchestrator() -> ChatOrchestrator:
    """Chat Orchestrator 인스턴스 반환"""
    global _chat_orchestrator
    if _chat_orchestrator is None:
        _chat_orchestrator = ChatOrchestrator()
    return _chat_orchestrator


# Request/Response 모델
class ChatRequest(BaseModel):
    """챗 요청"""

    message: str = Field(..., min_length=1, description="사용자 메시지")


class ChatResponse(BaseModel):
    """챗 응답"""

    response: str = Field(..., description="AI 응답")
    sources: list[str] = Field(default_factory=list, description="참고 문서 (선택)")


# API 엔드포인트
@router.post("", response_model=ChatResponse)
async def chat(
    request: Request,
    chat_request: ChatRequest,
) -> ChatResponse:
    """통합 Chat Orchestrator 기반 챗봇 대화."""
    # 프론트엔드에서 넘어온 메시지 출력
    print(f"💬 [챗봇] 프론트엔드에서 받은 메시지: '{chat_request.message}'")

    if not chat_request.message.strip():
        raise HTTPException(status_code=400, detail="메시지가 비어있습니다")

    try:
        orchestrator = get_chat_orchestrator()

        # app.state 에서 필요한 컨텍스트를 모아 오케스트레이터에 전달
        context = {
            "qlora_service": getattr(request.app.state, "qlora_service", None),
            "db_conn": getattr(request.app.state, "db_connection", None),
            "embedding_dim": getattr(request.app.state, "embedding_dimension", None),
            "chat_model": getattr(request.app.state, "chat_model", None),
        }

        result: ChatResult = await orchestrator.route_question(
            chat_request.message,
            context=context,
        )

        return ChatResponse(
            response=result.answer,
            sources=result.sources,
        )

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        print(f"❌ [챗봇] 오류 발생: {error_msg}")
        raise HTTPException(
            status_code=500,
            detail=f"챗봇 처리 중 오류 발생: {error_msg}"
        )
