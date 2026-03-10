"""RfP(Request for Proposal) 관련 스키마 정의.

RfP 문서 구조:
- 입찰 정보
- 요구사항 (Requirement)
- 평가 기준
- 제출 기한
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class RequirementType(str, Enum):
    """요구사항 타입."""
    TECHNICAL = "technical"  # 기술적 요구사항
    FUNCTIONAL = "functional"  # 기능적 요구사항
    ORGANIZATIONAL = "organizational"  # 조직 요구사항
    FINANCIAL = "financial"  # 재무 요구사항
    LEGAL = "legal"  # 법적 요구사항
    OTHER = "other"  # 기타


class RequirementPriority(str, Enum):
    """요구사항 우선순위."""
    MANDATORY = "mandatory"  # 필수
    HIGHLY_DESIRABLE = "highly_desirable"  # 강력 권장
    DESIRABLE = "desirable"  # 권장
    OPTIONAL = "optional"  # 선택


class Requirement(BaseModel):
    """RfP 요구사항."""
    
    id: str = Field(..., description="요구사항 고유 ID (예: REQ-001)")
    type: RequirementType = Field(..., description="요구사항 타입")
    priority: RequirementPriority = Field(..., description="우선순위")
    
    title: str = Field(..., description="요구사항 제목")
    description: str = Field(..., description="요구사항 상세 설명")
    
    # 위치 정보
    section: Optional[str] = Field(None, description="섹션 (예: '2.3 기술 요구사항')")
    page_number: Optional[int] = Field(None, description="페이지 번호")
    
    # 평가 기준
    evaluation_criteria: Optional[str] = Field(None, description="평가 기준")
    points: Optional[float] = Field(None, description="배점")
    
    # 관련 정보
    keywords: List[str] = Field(default_factory=list, description="키워드")
    references: List[str] = Field(default_factory=list, description="참조 문서")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "REQ-001",
                "type": "technical",
                "priority": "mandatory",
                "title": "클라우드 기반 인프라 구축",
                "description": "AWS 또는 Azure 기반의 확장 가능한 인프라를 구축해야 함",
                "section": "2.3 기술 요구사항",
                "page_number": 15,
                "evaluation_criteria": "클라우드 아키텍처 설계 능력",
                "points": 10.0,
                "keywords": ["클라우드", "AWS", "Azure", "인프라"],
                "references": []
            }
        }


class EvaluationCriteria(BaseModel):
    """평가 기준."""
    
    id: str = Field(..., description="평가 기준 ID")
    category: str = Field(..., description="평가 카테고리 (예: '기술력')")
    criterion: str = Field(..., description="평가 항목")
    weight: float = Field(..., description="가중치 (%)")
    max_points: float = Field(..., description="최대 점수")
    
    description: Optional[str] = Field(None, description="평가 기준 설명")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "EVAL-001",
                "category": "기술력",
                "criterion": "클라우드 아키텍처 설계",
                "weight": 20.0,
                "max_points": 20.0,
                "description": "AWS/Azure 기반 확장 가능한 아키텍처 설계 능력 평가"
            }
        }


class RfPMetadata(BaseModel):
    """RfP 메타데이터."""
    
    rfp_id: str = Field(..., description="RfP 고유 ID")
    title: str = Field(..., description="입찰 제목")
    organization: str = Field(..., description="발주 기관")
    
    # 날짜 정보
    published_date: Optional[datetime] = Field(None, description="공고일")
    submission_deadline: Optional[datetime] = Field(None, description="제출 마감일")
    evaluation_date: Optional[datetime] = Field(None, description="평가 예정일")
    
    # 예산 정보
    budget: Optional[float] = Field(None, description="예산 (원)")
    budget_currency: str = Field(default="KRW", description="통화")
    
    # 문서 정보
    total_pages: Optional[int] = Field(None, description="총 페이지 수")
    document_version: Optional[str] = Field(None, description="문서 버전")
    
    class Config:
        json_schema_extra = {
            "example": {
                "rfp_id": "RFP-2026-001",
                "title": "AI 기반 평가 시스템 구축",
                "organization": "KOICA",
                "published_date": "2026-02-01T00:00:00",
                "submission_deadline": "2026-03-15T18:00:00",
                "evaluation_date": "2026-03-20T00:00:00",
                "budget": 500000000.0,
                "budget_currency": "KRW",
                "total_pages": 80,
                "document_version": "1.0"
            }
        }


class RfPDocument(BaseModel):
    """RfP 문서 전체."""
    
    metadata: RfPMetadata = Field(..., description="메타데이터")
    requirements: List[Requirement] = Field(default_factory=list, description="요구사항 리스트")
    evaluation_criteria: List[EvaluationCriteria] = Field(
        default_factory=list, description="평가 기준 리스트"
    )
    
    # 추가 정보
    raw_text: Optional[str] = Field(None, description="원본 텍스트")
    extracted_tables: Optional[List[Dict[str, Any]]] = Field(
        None, description="추출된 표 데이터"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "metadata": {
                    "rfp_id": "RFP-2026-001",
                    "title": "AI 기반 평가 시스템 구축",
                    "organization": "KOICA"
                },
                "requirements": [],
                "evaluation_criteria": []
            }
        }


class RequirementExtractionRequest(BaseModel):
    """요구사항 추출 요청."""
    
    pdf_path: Optional[str] = Field(None, description="PDF 파일 경로")
    pdf_bytes: Optional[bytes] = Field(None, description="PDF 바이트 데이터")
    
    # 추출 옵션
    extract_tables: bool = Field(default=True, description="표 추출 여부")
    use_llm: bool = Field(default=True, description="LLM 사용 여부")
    
    class Config:
        json_schema_extra = {
            "example": {
                "pdf_path": "data/rfp/sample.pdf",
                "extract_tables": True,
                "use_llm": True
            }
        }


class RequirementExtractionResponse(BaseModel):
    """요구사항 추출 응답."""
    
    success: bool = Field(..., description="성공 여부")
    message: str = Field(..., description="메시지")
    
    document: Optional[RfPDocument] = Field(None, description="추출된 RfP 문서")
    
    # 통계
    total_requirements: int = Field(default=0, description="총 요구사항 수")
    mandatory_count: int = Field(default=0, description="필수 요구사항 수")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "요구사항 추출 완료",
                "document": None,
                "total_requirements": 25,
                "mandatory_count": 15
            }
        }
