"""일반 QA용 오케스트레이터.

KOICA/용어집 등 특정 도메인으로 분류되지 않은 질문을 처리한다.
"""

from __future__ import annotations

from asyncio import get_running_loop
from typing import Any, Dict, Optional

from app.domain.chat.bases.chat_result import ChatResult
from app.domain.chat.orchestrators.rag_orchestrator import run_rag_chat
from app.domain.chat.services.chat_service import ChatService


class GeneralOrchestrator:
    """일반 질문을 처리하는 오케스트레이터."""

    def __init__(self, chat_service: Optional[ChatService] = None) -> None:
        self._chat_service = chat_service or ChatService()

    async def process(self, question: str, context: Dict[str, Any]) -> ChatResult:
        """일반 질의 처리.

        1) Exaone QLoRA가 있으면 우선 사용
        2) 없으면 Exaone RAG (벡터 DB + Exaone/Gemini)
        3) 최종 fallback: Gemini ChatService
        """
        print(f"🌐 [GeneralOrchestrator] 일반 질의 수신: {question!r}")

        qlora_service = context.get("qlora_service")
        db_conn = context.get("db_conn")
        embedding_dim = context.get("embedding_dim")
        chat_model = context.get("chat_model")

        # 1) QLoRA 우선
        if qlora_service is not None and getattr(qlora_service, "is_loaded", False):
            print("🤖 [GeneralOrchestrator] Exaone QLoRA 모델 호출 중...")
            loop = get_running_loop()

            def call_qlora() -> str:
                return qlora_service.chat(
                    message=question,
                    history=None,
                    max_new_tokens=512,
                    temperature=0.7,
                    top_p=0.9,
                )

            response_text = await loop.run_in_executor(None, call_qlora)
            print(
                "🧭 [GeneralOrchestrator] Exaone QLoRA 생성 응답 반환",
                {"mode": "policy"},
            )

            return ChatResult(
                answer=response_text,
                sources=[],
                meta={"domain": "general", "mode": "policy", "backend": "qlora"},
            )

        # 2) QLoRA 없으면 Exaone RAG 그래프 또는 기존 chat_model 사용
        if db_conn is not None and embedding_dim is not None and chat_model is not None:
            print("🤖 [GeneralOrchestrator] Exaone RAG 그래프 호출 중...")
            loop = get_running_loop()

            def call_rag() -> str:
                return run_rag_chat(
                    user_text=question,
                    chat_model=chat_model,
                    db_conn=db_conn,
                    embedding_dim=embedding_dim,
                    system_prompt="당신은 KOICA 업무를 돕는 친절한 AI 어시스턴트입니다.",
                )

            response_text = await loop.run_in_executor(None, call_rag)
            print(
                "🧭 [GeneralOrchestrator] Exaone RAG 생성 응답 반환",
                {"mode": "policy"},
            )

            return ChatResult(
                answer=response_text,
                sources=[],
                meta={"domain": "general", "mode": "policy", "backend": "rag"},
            )

        # 3) 최종 Fallback: Gemini ChatService
        if not self._chat_service.is_available():
            msg = "현재 사용할 수 있는 채팅 모델이 없습니다. 나중에 다시 시도해 주세요."
            print(
                "⚠️ [GeneralOrchestrator] ChatService 사용 불가, Fallback 메시지 반환"
            )
            return ChatResult(
                answer=msg,
                sources=[],
                meta={"domain": "general", "mode": "unavailable"},
            )

        print("🤖 [GeneralOrchestrator] Gemini ChatService 호출 중 (최종 fallback)...")
        response_text = self._chat_service.chat(question)
        print(
            "🧭 [GeneralOrchestrator] Gemini 생성 응답 반환",
            {"mode": "policy"},
        )

        return ChatResult(
            answer=response_text,
            sources=[],
            meta={"domain": "general", "mode": "policy", "backend": "gemini"},
        )
