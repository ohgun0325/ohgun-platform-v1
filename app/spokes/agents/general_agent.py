"""일반 QA 도메인 에이전트.

GeneralChatOrchestrator를 래핑하여 에이전트 인터페이스를 제공합니다.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from app.domain.chat.bases.chat_result import ChatResult
from app.domain.koica.hub.orchestrators.general_orchestrator import (
    GeneralOrchestrator,
)


class GeneralAgent:
    """일반 질문을 처리하는 에이전트."""

    def __init__(
        self, orchestrator: Optional[GeneralOrchestrator] = None
    ) -> None:
        """에이전트 초기화.

        Args:
            orchestrator: GeneralOrchestrator 인스턴스 (None이면 새로 생성)
        """
        self._orchestrator = orchestrator or GeneralOrchestrator()

    async def process(
        self, question: str, context: Dict[str, Any]
    ) -> ChatResult:
        """일반 질의를 처리합니다.

        Args:
            question: 사용자 질문
            context: 컨텍스트 (qlora_service, db_conn, embedding_dim, chat_model 등)

        Returns:
            ChatResult: 처리 결과
        """
        return await self._orchestrator.process(question, context)

    @property
    def orchestrator(self) -> GeneralOrchestrator:
        """내부 오케스트레이터 인스턴스 반환."""
        return self._orchestrator
