"""평가(Evaluation) 관련 스키마 정의.

RfP와 Proposal을 비교 평가하는 시스템의 스키마입니다.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class MatchStatus(str, Enum):
    """매칭 상태."""
    FULLY_MATCHED = "fully_matched"  # 완전 일치
    PARTIALLY_MATCHED = "partially_matched"  # 부분 일치
    NOT_MATCHED = "not_matched"  # 불일치
    NOT_ADDRESSED = "not_addressed"  # 제안서에서 다루지 않음


class EvaluationScore(str, Enum):
    """평가 점수."""
    EXCELLENT = "excellent"  # 우수 (90-100%)
    GOOD = "good"  # 양호 (70-89%)
    FAIR = "fair"  # 보통 (50-69%)
    POOR = "poor"  # 미흡 (30-49%)
    VERY_POOR = "very_poor"  # 매우 미흡 (0-29%)


class RequirementMatch(BaseModel):
    """요구사항 매칭 결과."""
    
    requirement_id: str = Field(..., description="요구사항 ID")
    requirement_title: str = Field(..., description="요구사항 제목")
    requirement_priority: str = Field(..., description="우선순위")
    
    # 매칭 정보
    status: MatchStatus = Field(..., description="매칭 상태")
    matched_sections: List[str] = Field(
        default_factory=list,
        description="매칭된 제안서 섹션 ID 리스트"
    )
    
    # 점수
    score: Optional[float] = Field(None, description="점수 (0-100)")
    score_category: Optional[EvaluationScore] = Field(None, description="점수 카테고리")
    
    # 분석
    analysis: str = Field(default="", description="매칭 분석 내용")
    gaps: List[str] = Field(default_factory=list, description="부족한 점")
    strengths: List[str] = Field(default_factory=list, description="강점")
    
    class Config:
        json_schema_extra = {
            "example": {
                "requirement_id": "REQ-001",
                "requirement_title": "클라우드 기반 인프라 구축",
                "requirement_priority": "mandatory",
                "status": "fully_matched",
                "matched_sections": ["SEC-003", "SEC-004"],
                "score": 85.0,
                "score_category": "good",
                "analysis": "AWS 기반 아키텍처를 상세히 제안함",
                "gaps": [],
                "strengths": ["확장성 고려", "보안 설계 우수"]
            }
        }


class CategoryEvaluation(BaseModel):
    """카테고리별 평가."""
    
    category: str = Field(..., description="평가 카테고리")
    total_requirements: int = Field(..., description="총 요구사항 수")
    matched_requirements: int = Field(..., description="매칭된 요구사항 수")
    
    # 점수
    average_score: float = Field(..., description="평균 점수")
    max_score: float = Field(default=100.0, description="최대 점수")
    
    # 통계
    fully_matched_count: int = Field(default=0, description="완전 일치 개수")
    partially_matched_count: int = Field(default=0, description="부분 일치 개수")
    not_matched_count: int = Field(default=0, description="불일치 개수")
    
    class Config:
        json_schema_extra = {
            "example": {
                "category": "기술 요구사항",
                "total_requirements": 10,
                "matched_requirements": 8,
                "average_score": 78.5,
                "max_score": 100.0,
                "fully_matched_count": 5,
                "partially_matched_count": 3,
                "not_matched_count": 2
            }
        }


class EvaluationReport(BaseModel):
    """평가 보고서."""
    
    # 기본 정보
    report_id: str = Field(..., description="보고서 ID")
    rfp_id: str = Field(..., description="RfP ID")
    proposal_id: str = Field(..., description="제안서 ID")
    
    evaluation_date: datetime = Field(..., description="평가 날짜")
    evaluator: Optional[str] = Field(None, description="평가자")
    
    # 전체 점수
    total_score: float = Field(..., description="총점")
    max_score: float = Field(default=100.0, description="최대 점수")
    percentage: float = Field(..., description="백분율 (%)")
    
    # 매칭 결과
    requirement_matches: List[RequirementMatch] = Field(
        default_factory=list,
        description="요구사항별 매칭 결과"
    )
    
    # 카테고리별 평가
    category_evaluations: List[CategoryEvaluation] = Field(
        default_factory=list,
        description="카테고리별 평가"
    )
    
    # 종합 분석
    summary: str = Field(default="", description="종합 요약")
    strengths: List[str] = Field(default_factory=list, description="전체 강점")
    weaknesses: List[str] = Field(default_factory=list, description="전체 약점")
    recommendations: List[str] = Field(
        default_factory=list,
        description="개선 권고사항"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "report_id": "EVAL-2026-001",
                "rfp_id": "RFP-2026-001",
                "proposal_id": "PROP-2026-001",
                "evaluation_date": "2026-03-15T10:00:00",
                "evaluator": "AI Evaluator",
                "total_score": 78.5,
                "max_score": 100.0,
                "percentage": 78.5,
                "requirement_matches": [],
                "category_evaluations": [],
                "summary": "전반적으로 우수한 제안서입니다.",
                "strengths": ["기술력 우수", "팀 구성 탁월"],
                "weaknesses": ["일정 계획 부족"],
                "recommendations": ["일정을 더 상세히 작성하세요"]
            }
        }


class EvaluationRequest(BaseModel):
    """평가 요청."""
    
    rfp_id: str = Field(..., description="RfP ID")
    proposal_id: str = Field(..., description="제안서 ID")
    
    # 평가 옵션
    use_llm: bool = Field(default=True, description="LLM 사용 여부")
    detailed_analysis: bool = Field(default=True, description="상세 분석 여부")
    
    # 평가자 정보
    evaluator: Optional[str] = Field(None, description="평가자 이름")
    
    class Config:
        json_schema_extra = {
            "example": {
                "rfp_id": "RFP-2026-001",
                "proposal_id": "PROP-2026-001",
                "use_llm": True,
                "detailed_analysis": True,
                "evaluator": "John Doe"
            }
        }


class EvaluationResponse(BaseModel):
    """평가 응답."""
    
    success: bool = Field(..., description="성공 여부")
    message: str = Field(..., description="메시지")
    
    report: Optional[EvaluationReport] = Field(None, description="평가 보고서")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "평가 완료",
                "report": None
            }
        }


class RuleValidationResult(BaseModel):
    """규칙 검증 결과."""
    
    rule_id: str = Field(..., description="규칙 ID")
    rule_description: str = Field(..., description="규칙 설명")
    
    passed: bool = Field(..., description="통과 여부")
    severity: str = Field(..., description="심각도 (critical, high, medium, low)")
    
    message: str = Field(..., description="검증 메시지")
    details: Optional[str] = Field(None, description="상세 내용")
    
    class Config:
        json_schema_extra = {
            "example": {
                "rule_id": "RULE-001",
                "rule_description": "제안서 총 페이지는 100페이지를 초과할 수 없음",
                "passed": True,
                "severity": "high",
                "message": "페이지 수 요구사항 충족",
                "details": "제안서: 85페이지 / 최대: 100페이지"
            }
        }
