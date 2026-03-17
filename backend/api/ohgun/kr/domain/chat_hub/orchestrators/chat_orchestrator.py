"""통합 Chat Orchestrator.

질문을 받아 QuestionClassifier 로 도메인을 분류하고,
각 도메인별 오케스트레이터로 라우팅한다.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, Optional

from domain.chat_hub.bases.chat_result import ChatResult
from domain.chat_hub.services.question_classifier import QuestionClassifier
from domain.chat_hub.services.question_classifier import QuestionClassification
from domain.koica.hub.orchestrators.koica_orchestrator import (
    KoicaOrchestrator,
)
from domain.soccer.hub.orchestrators.soccer_orchestrator import (
    SoccerOrchestrator,
)


class ChatOrchestrator:
    """전체 챗봇 흐름을 조율하는 오케스트레이터."""

    def __init__(
        self,
        classifier: Optional[QuestionClassifier] = None,
        koica_orchestrator: Optional[KoicaOrchestrator] = None,
        soccer_orchestrator: Optional[SoccerOrchestrator] = None,
    ) -> None:
        self._classifier = classifier or QuestionClassifier()
        self._koica_orch = koica_orchestrator or KoicaOrchestrator()
        self._soccer_orch = soccer_orchestrator or SoccerOrchestrator()

    async def route_question(
        self,
        question: str,
        context: Dict[str, Any],
    ) -> ChatResult:
        """질문을 분류하고, 적절한 도메인 오케스트레이터로 전달한다."""
        classification: QuestionClassification = self._classifier.classify(question)

        print(
            "🧭 [ChatOrchestrator] 질문 분류 결과",
            {
                "question": question,
                "classification": asdict(classification),
            },
        )

        domain = classification.domain

        # soccer → SoccerOrchestrator (Tool 직접 연결)
        if domain == "soccer":
            context_with_domain = {**context, "domain": domain}
            result = await self._soccer_orch.process(question, context_with_domain)
        # term, koica, general → Koica 도메인
        # (General = 데이터셋에 없을 때 Exaone이 Koica 맥락으로 답 생성하는 fallback)
        else:
            context_with_domain = {**context, "domain": domain}
            result = await self._koica_orch.process(question, context_with_domain)

        # meta 에 분류 결과를 포함시켜 추후 로깅/분석에 활용할 수 있도록 한다.
        result.meta.setdefault("classification", asdict(classification))
        return result

