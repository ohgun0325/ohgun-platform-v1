"""제안서(Proposal) 관련 스키마 정의.

제안서 구조:
- 메타데이터
- 목차 (TOC)
- 섹션별 내용
- 첨부 파일
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class SectionType(str, Enum):
    """섹션 타입."""
    COVER = "cover"  # 표지
    TOC = "toc"  # 목차
    EXECUTIVE_SUMMARY = "executive_summary"  # 요약
    INTRODUCTION = "introduction"  # 서론
    BACKGROUND = "background"  # 배경
    OBJECTIVES = "objectives"  # 목표
    APPROACH = "approach"  # 접근 방법
    METHODOLOGY = "methodology"  # 방법론
    TIMELINE = "timeline"  # 일정
    BUDGET = "budget"  # 예산
    TEAM = "team"  # 팀 구성
    QUALIFICATIONS = "qualifications"  # 자격 요건
    REFERENCES = "references"  # 참고 문헌
    APPENDIX = "appendix"  # 부록
    OTHER = "other"  # 기타


class ProposalSection(BaseModel):
    """제안서 섹션."""
    
    id: str = Field(..., description="섹션 고유 ID")
    type: SectionType = Field(..., description="섹션 타입")
    
    title: str = Field(..., description="섹션 제목")
    level: int = Field(..., description="목차 레벨 (1=챕터, 2=섹션, 3=서브섹션)")
    
    # 내용
    content: str = Field(default="", description="섹션 내용")
    
    # 위치 정보
    page_start: Optional[int] = Field(None, description="시작 페이지")
    page_end: Optional[int] = Field(None, description="끝 페이지")
    
    # 하위 섹션
    subsections: List[ProposalSection] = Field(default_factory=list, description="하위 섹션")
    
    # 추가 정보
    tables: List[Dict[str, Any]] = Field(default_factory=list, description="표 데이터")
    images: List[Dict[str, Any]] = Field(default_factory=list, description="이미지 정보")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "SEC-001",
                "type": "approach",
                "title": "기술 접근 방법",
                "level": 1,
                "content": "본 프로젝트는 클라우드 기반 아키텍처를 채택합니다...",
                "page_start": 10,
                "page_end": 15,
                "subsections": [],
                "tables": [],
                "images": []
            }
        }


class TableOfContents(BaseModel):
    """목차."""
    
    entries: List[TOCEntry] = Field(default_factory=list, description="목차 항목")
    
    class Config:
        json_schema_extra = {
            "example": {
                "entries": [
                    {
                        "title": "1. 서론",
                        "page": 3,
                        "level": 1
                    },
                    {
                        "title": "2. 기술 접근 방법",
                        "page": 10,
                        "level": 1
                    }
                ]
            }
        }


class TOCEntry(BaseModel):
    """목차 항목."""
    
    title: str = Field(..., description="항목 제목")
    page: int = Field(..., description="페이지 번호")
    level: int = Field(..., description="레벨 (1, 2, 3...)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "title": "1. 서론",
                "page": 3,
                "level": 1
            }
        }


class ProposalMetadata(BaseModel):
    """제안서 메타데이터."""
    
    proposal_id: str = Field(..., description="제안서 고유 ID")
    title: str = Field(..., description="제안서 제목")
    
    # 제출 정보
    organization: str = Field(..., description="제안 기관/회사")
    submission_date: Optional[datetime] = Field(None, description="제출일")
    
    # RfP 연결
    rfp_id: Optional[str] = Field(None, description="관련 RfP ID")
    
    # 문서 정보
    total_pages: Optional[int] = Field(None, description="총 페이지 수")
    version: Optional[str] = Field(None, description="버전")
    
    # 연락처
    contact_person: Optional[str] = Field(None, description="담당자")
    contact_email: Optional[str] = Field(None, description="이메일")
    contact_phone: Optional[str] = Field(None, description="전화번호")
    
    class Config:
        json_schema_extra = {
            "example": {
                "proposal_id": "PROP-2026-001",
                "title": "AI 기반 평가 시스템 구축 제안서",
                "organization": "KPMG Korea",
                "submission_date": "2026-03-10T00:00:00",
                "rfp_id": "RFP-2026-001",
                "total_pages": 120,
                "version": "1.0",
                "contact_person": "홍길동",
                "contact_email": "hong@kpmg.com",
                "contact_phone": "02-1234-5678"
            }
        }


class ProposalDocument(BaseModel):
    """제안서 문서 전체."""
    
    metadata: ProposalMetadata = Field(..., description="메타데이터")
    toc: Optional[TableOfContents] = Field(None, description="목차")
    sections: List[ProposalSection] = Field(default_factory=list, description="섹션 리스트")
    
    # 원본 데이터
    raw_text: Optional[str] = Field(None, description="원본 텍스트")
    
    class Config:
        json_schema_extra = {
            "example": {
                "metadata": {
                    "proposal_id": "PROP-2026-001",
                    "title": "AI 기반 평가 시스템 구축 제안서",
                    "organization": "KPMG Korea"
                },
                "toc": None,
                "sections": [],
                "raw_text": None
            }
        }


class ProposalParsingRequest(BaseModel):
    """제안서 파싱 요청."""
    
    pdf_path: Optional[str] = Field(None, description="PDF 파일 경로")
    pdf_bytes: Optional[bytes] = Field(None, description="PDF 바이트 데이터")
    
    # 파싱 옵션
    extract_toc: bool = Field(default=True, description="목차 추출 여부")
    extract_tables: bool = Field(default=True, description="표 추출 여부")
    use_llm: bool = Field(default=False, description="LLM 사용 여부")
    
    class Config:
        json_schema_extra = {
            "example": {
                "pdf_path": "data/proposals/sample.pdf",
                "extract_toc": True,
                "extract_tables": True,
                "use_llm": False
            }
        }


class ProposalParsingResponse(BaseModel):
    """제안서 파싱 응답."""
    
    success: bool = Field(..., description="성공 여부")
    message: str = Field(..., description="메시지")
    
    document: Optional[ProposalDocument] = Field(None, description="파싱된 제안서 문서")
    
    # 통계
    total_sections: int = Field(default=0, description="총 섹션 수")
    total_pages: int = Field(default=0, description="총 페이지 수")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "제안서 파싱 완료",
                "document": None,
                "total_sections": 10,
                "total_pages": 120
            }
        }
