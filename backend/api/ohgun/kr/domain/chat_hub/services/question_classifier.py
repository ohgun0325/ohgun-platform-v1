"""질문 도메인 분류기 (term / koica / general).

초기 버전은 가벼운 **룰 기반** 분류만 수행하고,
추후 필요 시 KoElectra 등의 다중 클래스 분류기로 교체할 수 있도록
인터페이스를 단순하게 유지합니다.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Literal


DomainLabel = Literal["term", "koica", "general"]


@dataclass(frozen=True)
class QuestionClassification:
    """질문 분류 결과."""

    domain: DomainLabel
    confidence: float
    scores: Dict[DomainLabel, float]
    method: str  # "rule_based", "ml", "fallback" 등


class QuestionClassifier:
    """질문을 term / koica / general 중 하나로 분류하는 간단한 분류기."""

    def __init__(self) -> None:
        # 키워드 목록은 향후 환경설정/DB 등으로 분리 가능
        self._term_keywords = [
            "용어",
            "뜻",
            "의미",
            "정의",
            "약어",
            "풀어 써",
            "무엇의 약자",
            "무엇의 뜻",
        ]
        self._koica_keywords = [
            "koica",
            "코이카",
            "사업",
            "프로젝트",
            "oda",
            "공적개발원조",
        ]

    def classify(self, text: str) -> QuestionClassification:
        """질문 텍스트를 기반으로 도메인을 분류합니다.

        현재는 간단한 룰 기반 분류만 수행합니다.
        """
        normalized = text.strip().lower()

        if not normalized:
            # 비어있는 경우에는 일반 질의로 취급하되, 신뢰도는 0으로 둔다.
            scores: Dict[DomainLabel, float] = {
                "term": 0.0,
                "koica": 0.0,
                "general": 1.0,
            }
            return QuestionClassification(
                domain="general",
                confidence=0.0,
                scores=scores,
                method="fallback",
            )

        term_score = self._score_for_keywords(normalized, self._term_keywords)
        koica_score = self._score_for_keywords(normalized, self._koica_keywords)

        # 기본 general 점수는 0.5에서 시작하고,
        # term/koica 스코어가 높을수록 상대적으로 줄어든다고 가정.
        general_score = max(
            0.0, 0.5 - max(term_score, koica_score) / 2
        )

        scores = {
            "term": term_score,
            "koica": koica_score,
            "general": general_score,
        }

        # 가장 높은 스코어를 갖는 도메인 선택
        domain: DomainLabel = max(scores, key=lambda k: scores[k])  # type: ignore[assignment]
        confidence = float(scores[domain])

        return QuestionClassification(
            domain=domain,
            confidence=confidence,
            scores=scores,
            method="rule_based",
        )

    @staticmethod
    def _score_for_keywords(text: str, keywords: list[str]) -> float:
        """아주 단순한 키워드 기반 스코어 계산.

        - 포함된 키워드 개수에 비례해서 0~1 사이 값을 반환한다.
        """
        if not keywords:
            return 0.0

        hits = 0
        for kw in keywords:
            if kw.lower() in text:
                hits += 1

        if hits == 0:
            return 0.0

        # 너무 과하지 않게 0.3~1.0 사이로 매핑
        base = 0.3
        score = base + (hits / len(keywords)) * (1.0 - base)
        return min(score, 1.0)

