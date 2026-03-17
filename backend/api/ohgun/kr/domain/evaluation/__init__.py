"""Evaluation 도메인.

RfP와 제안서를 비교 평가합니다.

주요 기능:
- 요구사항 매칭
- 규칙 검증
- 점수 계산
- 평가 보고서 생성
"""

from domain.evaluation.schemas import (
    MatchStatus,
    EvaluationScore,
    RequirementMatch,
    CategoryEvaluation,
    EvaluationReport,
    EvaluationRequest,
    EvaluationResponse,
    RuleValidationResult,
)

from domain.evaluation.services import (
    Matcher,
    RuleValidator,
    ReportGenerator,
)

from domain.evaluation.orchestrators import (
    EvaluationOrchestrator,
)

__all__ = [
    # Schemas
    "MatchStatus",
    "EvaluationScore",
    "RequirementMatch",
    "CategoryEvaluation",
    "EvaluationReport",
    "EvaluationRequest",
    "EvaluationResponse",
    "RuleValidationResult",
    # Services
    "Matcher",
    "RuleValidator",
    "ReportGenerator",
    # Orchestrators
    "EvaluationOrchestrator",
]
