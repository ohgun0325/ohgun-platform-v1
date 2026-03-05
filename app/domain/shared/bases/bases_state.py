"""LangGraph 상태 스키마 베이스 정의."""

from typing import Any, Dict, List, TypedDict


class BaseProcessingState(TypedDict):
    """LangGraph 상태 스키마 베이스 클래스.

    데이터 처리 상태의 기본 스키마.
    모든 도메인(Player, Team, Stadium, Schedule)의 상태 스키마가 상속받는 베이스 클래스.
    """

    # 입력 데이터
    items: List[Dict[str, Any]]
    # 검증 결과
    validation_errors: List[Dict[str, Any]]
    # 전략 판단 결과
    strategy_type: str  # "policy" | "rule"
    # 최종 결과
    final_result: Dict[str, Any]
