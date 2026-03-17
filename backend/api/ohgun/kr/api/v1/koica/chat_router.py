"""KOICA Chat API - soccer의 player_router / schedule_router 등과 동일한 역할.

KOICA 도메인 내 '채팅' 기능 전용 라우터.
"""

from fastapi import APIRouter, HTTPException, Request
from typing import Optional, Union

from core.chat_chain import chat_with_ai
from schemas import ChatRequest, ChatResponse
from artifacts.models.interfaces.base import BaseLLMModel

try:
    from langchain_google_genai import ChatGoogleGenerativeAI
except ImportError:
    ChatGoogleGenerativeAI = None  # type: ignore

router = APIRouter(prefix="/chat", tags=["koica", "chat"])


@router.post("", response_model=ChatResponse)
async def chat(request: Request, chat_request: ChatRequest) -> ChatResponse:
    """KOICA 채팅 (RAG 기반).

    Args:
        request: FastAPI request object.
        chat_request: Chat request with user message.

    Returns:
        Chat response with AI's answer and sources.

    Raises:
        HTTPException: If database is not connected or other errors occur.
    """
    db_conn = request.app.state.db_connection
    embedding_dim = request.app.state.embedding_dimension
    chat_model: Optional[Union[BaseLLMModel, ChatGoogleGenerativeAI]] = getattr(
        request.app.state, "chat_model", None
    )
    qlora_service = getattr(request.app.state, "qlora_service", None)

    if qlora_service and qlora_service.is_loaded:
        chat_model = qlora_service

    if not db_conn:
        raise HTTPException(status_code=503, detail="데이터베이스 연결 없음")

    if not chat_request.message.strip():
        raise HTTPException(status_code=400, detail="메시지가 비어있습니다")

    try:
        response_text = chat_with_ai(
            conn=db_conn,
            user_input=chat_request.message,
            dimension=embedding_dim,
            chat_model=chat_model,
        )
        sources: list[str] = []
        return ChatResponse(response=response_text, sources=sources)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"채팅 처리 중 오류 발생: {str(e)}"
        )
