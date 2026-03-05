"""선수 업로드 파이프라인 오케스트레이션 모듈.

GoF 전략(Strategy) 패턴을 이용해 정책 기반 / 규칙 기반 전략을 선택하고 실행합니다.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from artifacts.models.core.manager import ModelManager
from artifacts.models.interfaces.base import BaseLLMModel
from app.domain.soccer.agents.player_agent import PlayerAgent
from app.domain.soccer.services.player_service import PlayerService


class PlayerStrategyType(str, Enum):
    """플레이어 처리 전략 유형."""

    POLICY = "policy"  # 정책 기반 / LLM 에이전트
    RULE_BASED = "rule_based"  # 전통적인 규칙 기반 서비스


@dataclass
class StrategyDecision:
    """전략 선택 결과."""

    strategy: PlayerStrategyType
    confidence: float = 0.0
    raw_scores: Optional[Dict[str, float]] = None
    raw_output: Optional[Dict[str, Any]] = None


class PlayerProcessingStrategy:
    """전략 패턴용 공통 인터페이스."""

    def process(
        self,
        records: List[Dict[str, Any]],
        data_type: str,
        file_name: Optional[str] = None,
        decision: Optional[StrategyDecision] = None,
    ) -> Dict[str, Any]:
        raise NotImplementedError


class PolicyBasedPlayerStrategy(PlayerProcessingStrategy):
    """정책 기반(LLM 에이전트) 전략."""

    def __init__(self, agent: Optional[PlayerAgent] = None) -> None:
        self.agent = agent or PlayerAgent(
            model_name="monolog/koelectra-small-v3-discriminator"
        )

    def process(
        self,
        records: List[Dict[str, Any]],
        data_type: str,
        file_name: Optional[str] = None,
        decision: Optional[StrategyDecision] = None,
    ) -> Dict[str, Any]:
        result = self.agent.process(records, data_type=data_type, file_name=file_name)
        if decision:
            result["decision"] = {
                "strategy": decision.strategy.value,
                "confidence": decision.confidence,
                "scores": decision.raw_scores,
            }
        return result


class RuleBasedPlayerStrategy(PlayerProcessingStrategy):
    """규칙 기반 서비스 전략."""

    def __init__(self, service: Optional[PlayerService] = None) -> None:
        self.service = service or PlayerService()

    def process(
        self,
        records: List[Dict[str, Any]],
        data_type: str,
        file_name: Optional[str] = None,
        decision: Optional[StrategyDecision] = None,
    ) -> Dict[str, Any]:
        result = self.service.validate_and_summarize(
            records, data_type=data_type, file_name=file_name
        )
        if decision:
            result["decision"] = {
                "strategy": decision.strategy.value,
                "confidence": decision.confidence,
                "scores": decision.raw_scores,
            }
        return result


class PlayerOrchestrator:
    """선수 업로드에 대한 전략 선택 및 실행을 담당하는 오케스트레이터."""

    def __init__(
        self,
        classifier_model_name: str = "monolog/koelectra-small-v3-discriminator",
        model_manager: Optional[ModelManager] = None,
    ) -> None:
        self.classifier_model_name = classifier_model_name
        self._model_manager = model_manager or ModelManager()
        self._classifier: Optional[BaseLLMModel] = None
        self._policy_strategy = PolicyBasedPlayerStrategy()
        self._rule_strategy = RuleBasedPlayerStrategy()

    # ------------------------------------------------------------------
    # 전략 선택 (분류기 호출)
    # ------------------------------------------------------------------
    def _ensure_classifier(self) -> Optional[BaseLLMModel]:
        if self._classifier is None:
            self._classifier = self._model_manager.get_chat_model(
                self.classifier_model_name
            )
            if self._classifier is None:
                print(
                    f"⚠️ 전략 분류용 LLM을 로드하지 못했습니다. 기본적으로 rule_based 전략을 사용합니다. "
                    f"(model={self.classifier_model_name})"
                )
        return self._classifier

    def _build_classification_prompt(
        self,
        preview_records: List[Dict[str, Any]],
        data_type: str,
    ) -> List[Dict[str, str]]:
        """전략 분류용 LLM 프롬프트 생성."""
        example_lines = []
        for idx, row in enumerate(preview_records[:5], start=1):
            try:
                example_lines.append(f"[{idx}] {json.dumps(row, ensure_ascii=False)}")
            except TypeError:
                example_lines.append(f"[{idx}] {row}")

        user_content = (
            "다음은 축구 도메인의 데이터셋 일부입니다.\n"
            f"- 데이터 타입: {data_type}\n"
            "- 아래 예시는 JSON Lines 포맷의 일부 행입니다.\n\n"
            + "\n".join(example_lines)
            + "\n\n"
            "이 데이터를 처리할 때 어떤 접근이 더 적합한지 판단해 주세요.\n"
            "1) 정책 기반(Policy-based, LLM/ML 모델이 규칙을 학습해서 판단)\n"
            "2) 규칙 기반(Rule-based, 사람이 정의한 명시적 규칙으로 처리)\n\n"
            "출력은 반드시 다음 JSON 형식으로만 응답하세요:\n"
            '{"label": "policy" 또는 "rule_based", "scores": {"policy": "확률", "rule_based": "확률"}}\n'
        )

        system_content = (
            "당신은 데이터 파이프라인 설계를 돕는 ML 전문가입니다. "
            "주어진 예시 데이터를 보고, 정책 기반(ML/LLM) 접근이 적절한지, "
            "단순 규칙 기반으로 충분한지 판단합니다."
        )

        return [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content},
        ]

    def classify_strategy(self, preview_records: List[Dict[str, Any]], data_type: str) -> StrategyDecision:
        """LLM 또는 휴리스틱을 사용해 어떤 전략을 쓸지 결정합니다."""
        model = self._ensure_classifier()
        if model is None:
            # 분류 모델이 없으면 기본적으로 규칙 기반으로 처리
            return StrategyDecision(strategy=PlayerStrategyType.RULE_BASED, confidence=0.0)

        messages = self._build_classification_prompt(preview_records, data_type)
        raw = model.invoke(messages)

        try:
            parsed = json.loads(raw)
            label = str(parsed.get("label", "")).lower()
            scores = parsed.get("scores") or {}
            if label not in {s.value for s in PlayerStrategyType}:
                # label이 이상하면 점수 기반으로 결정
                policy_score = float(scores.get("policy", 0.0))
                rule_score = float(scores.get("rule_based", 0.0))
                if policy_score >= rule_score:
                    label = PlayerStrategyType.POLICY.value
                else:
                    label = PlayerStrategyType.RULE_BASED.value
            strategy = (
                PlayerStrategyType.POLICY
                if label == PlayerStrategyType.POLICY.value
                else PlayerStrategyType.RULE_BASED
            )
            confidence = float(max(scores.values()) if scores else 0.0)
            return StrategyDecision(
                strategy=strategy,
                confidence=confidence,
                raw_scores={k: float(v) for k, v in scores.items()},
                raw_output=parsed,
            )
        except Exception as e:  # 파싱 실패 시 단순 휴리스틱
            print(f"⚠️ 전략 분류 응답 파싱 실패, 휴리스틱으로 대체합니다: {e}")
            lower = raw.lower()
            if "policy" in lower or "정책" in lower:
                strategy = PlayerStrategyType.POLICY
            else:
                strategy = PlayerStrategyType.RULE_BASED
            return StrategyDecision(strategy=strategy, confidence=0.0, raw_output={"raw": raw})

    # ------------------------------------------------------------------
    # 퍼사드 메서드
    # ------------------------------------------------------------------
    async def route_players(
        self,
        records: List[Dict[str, Any]],
        data_type: str,
        file_name: Optional[str] = None,
    ) -> Tuple[StrategyDecision, Dict[str, Any]]:
        """전략을 결정하고 해당 전략으로 데이터를 처리합니다."""

        loop = asyncio.get_running_loop()
        preview = records[:5]

        # 분류는 블로킹 연산일 수 있으므로 스레드 풀에서 실행
        decision: StrategyDecision = await loop.run_in_executor(
            None, self.classify_strategy, preview, data_type
        )

        # 선수 업로드 파이프라인에서는 데이터 적재를 보장하기 위해
        # 최종 실행 전략은 휴리스틱을 우선시한다.
        # - 기본값: 분류 결과 전략
        # - 예외: data_type 이 "players" 인 경우에는 항상 규칙 기반 전략으로 저장을 수행
        effective_strategy = decision.strategy
        if data_type == "players":
            effective_strategy = PlayerStrategyType.RULE_BASED

        if effective_strategy == PlayerStrategyType.POLICY:
            result = await loop.run_in_executor(
                None,
                self._policy_strategy.process,
                records,
                data_type,
                file_name,
                decision,
            )
        else:
            result = await loop.run_in_executor(
                None,
                self._rule_strategy.process,
                records,
                data_type,
                file_name,
                decision,
            )

        return decision, result
