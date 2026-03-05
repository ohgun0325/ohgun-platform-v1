"""통합 Chat 에이전트.

ChatOrchestrator를 래핑하여 에이전트 인터페이스를 제공합니다.
Exaone 모델 로드 기능 포함.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from app.domain.chat.bases.chat_result import ChatResult
from app.domain.chat.orchestrators.chat_orchestrator import ChatOrchestrator
from artifacts.models.core.manager import ModelManager
from artifacts.models.interfaces.base import BaseLLMModel


class ChatAgent:
    """전체 챗봇 흐름을 조율하는 통합 에이전트."""

    def __init__(
        self,
        orchestrator: Optional[ChatOrchestrator] = None,
        exaone_model_name: Optional[str] = None,
    ) -> None:
        """에이전트 초기화.

        Args:
            orchestrator: ChatOrchestrator 인스턴스 (None이면 새로 생성)
            exaone_model_name: Exaone 모델 이름 (None이면 설정에서 기본값 사용)
        """
        self._orchestrator = orchestrator or ChatOrchestrator()
        self._model_manager = ModelManager()
        self._exaone_model: Optional[BaseLLMModel] = None
        self._exaone_model_name = exaone_model_name

    def load_exaone(self, model_name: Optional[str] = None) -> bool:
        """Exaone 모델을 로드합니다.

        Args:
            model_name: 모델 이름 (None이면 초기화 시 지정한 값 또는 기본값 사용)

        Returns:
            로드 성공 여부
        """
        model_name = model_name or self._exaone_model_name
        if model_name is None:
            # 기본 Exaone 모델 이름 (설정에서 가져오거나 하드코딩)
            model_name = "exaone-2.4b"

        print(f"📦 [ChatAgent] Exaone 모델 로드 시도: {model_name}")
        self._exaone_model = self._model_manager.get_chat_model(model_name)

        if self._exaone_model is None or not self._exaone_model.is_loaded:
            print(f"⚠️ [ChatAgent] Exaone 모델 로드 실패: {model_name}")
            return False

        print(f"✅ [ChatAgent] Exaone 모델 로드 완료: {model_name}")
        self._exaone_model_name = model_name
        return True

    @property
    def exaone_model(self) -> Optional[BaseLLMModel]:
        """로드된 Exaone 모델 인스턴스 반환."""
        return self._exaone_model

    @property
    def is_exaone_loaded(self) -> bool:
        """Exaone 모델이 로드되어 있는지 여부."""
        return self._exaone_model is not None and self._exaone_model.is_loaded

    async def route_question(
        self, question: str, context: Dict[str, Any]
    ) -> ChatResult:
        """질문을 분류하고 적절한 도메인 에이전트로 라우팅합니다.

        Args:
            question: 사용자 질문
            context: 컨텍스트 (qlora_service, db_conn, embedding_dim, chat_model 등)

        Returns:
            ChatResult: 처리 결과
        """
        # Exaone 모델이 로드되어 있으면 context에 추가
        if self.is_exaone_loaded and self._exaone_model:
            context["exaone_model"] = self._exaone_model

        return await self._orchestrator.route_question(question, context)

    @property
    def orchestrator(self) -> ChatOrchestrator:
        """내부 오케스트레이터 인스턴스 반환."""
        return self._orchestrator
