"""용어집(ODA 용어사전) 도메인 에이전트.

TermChatOrchestrator를 래핑하여 에이전트 인터페이스를 제공합니다.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from app.domain.chat.bases.chat_result import ChatResult
from app.domain.koica.hub.orchestrators.term_orchestrator import TermOrchestrator


class TermAgent:
    """용어집 질의를 처리하는 에이전트."""

    def __init__(
        self, orchestrator: Optional[TermOrchestrator] = None
    ) -> None:
        """에이전트 초기화.

        Args:
            orchestrator: TermOrchestrator 인스턴스 (None이면 새로 생성)
        """
        self._orchestrator = orchestrator or TermOrchestrator()

    async def process(self, question: str) -> ChatResult:
        """용어 질의를 처리합니다.

        Args:
            question: 사용자 질문

        Returns:
            ChatResult: 처리 결과
        """
        return await self._orchestrator.process(question)

    @property
    def orchestrator(self) -> TermOrchestrator:
        """내부 오케스트레이터 인스턴스 반환."""
        return self._orchestrator
