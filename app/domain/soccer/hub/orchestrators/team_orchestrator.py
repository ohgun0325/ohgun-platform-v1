"""팀 업로드 파이프라인 오케스트레이션 모듈.

현재는 규칙 기반(TeamService)만 사용하지만,
GoF 전략(Strategy) 패턴의 형태를 유지하여 추후 정책 기반 전략을 추가하기 쉽도록 구성합니다.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional, Tuple

from app.domain.soccer.hub.orchestrators.player_orchestrator import (
    PlayerStrategyType,
    StrategyDecision,
)
from app.domain.soccer.services.team_service import TeamService


class TeamOrchestrator:
    """팀 업로드에 대한 전략 선택 및 실행을 담당하는 오케스트레이터.

    - 현재는 규칙 기반(TeamService) 하나만 사용
    - 그러나 PlayerStrategyType/StrategyDecision 을 재사용하여
      응답 스키마와 메타데이터 구조를 player 파이프라인과 동일하게 유지
    """

    def __init__(self, service: Optional[TeamService] = None) -> None:
        self._service = service or TeamService()

    async def route_teams(
        self,
        records: List[Dict[str, Any]],
        data_type: str,
        file_name: Optional[str] = None,
    ) -> Tuple[StrategyDecision, Dict[str, Any]]:
        """전략을 결정하고 해당 전략으로 데이터를 처리합니다.

        현재는 분류기/LLM 없이 규칙 기반(rule_based) 전략으로 고정합니다.
        """
        loop = asyncio.get_running_loop()

        decision = StrategyDecision(
            strategy=PlayerStrategyType.RULE_BASED,
            confidence=1.0,
            raw_scores={"rule_based": 1.0},
            raw_output={"reason": "Team 도메인은 현재 규칙 기반 처리로 고정"},
        )

        result: Dict[str, Any] = await loop.run_in_executor(
            None,
            self._service.validate_and_summarize,
            records,
            data_type,
            file_name,
        )

        # player 파이프라인과 동일한 메타데이터를 포함하도록 보강
        result.setdefault(
            "decision",
            {
                "strategy": decision.strategy.value,
                "confidence": decision.confidence,
                "scores": decision.raw_scores,
            },
        )

        return decision, result

