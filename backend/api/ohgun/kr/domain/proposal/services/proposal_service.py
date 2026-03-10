"""제안서 서비스.

제안서 처리의 비즈니스 로직을 담당합니다.
"""

from __future__ import annotations

from pathlib import Path
from typing import Union, Optional, List

from app.domain.proposal.schemas.proposal_schema import (
    ProposalDocument,
    ProposalSection,
    ProposalParsingResponse,
)
from app.domain.proposal.parsers.proposal_pdf_parser import ProposalPDFParser


class ProposalService:
    """제안서 서비스."""
    
    def __init__(self):
        """초기화."""
        self.pdf_parser = ProposalPDFParser(use_pdfplumber=True)
    
    def process_proposal_pdf(
        self,
        pdf_source: Union[str, Path, bytes],
    ) -> ProposalParsingResponse:
        """제안서 PDF를 처리합니다.
        
        Args:
            pdf_source: PDF 파일 경로 또는 바이트 데이터
            
        Returns:
            파싱 응답
        """
        try:
            # PDF 파싱
            document = self.pdf_parser.parse(pdf_source)
            
            return ProposalParsingResponse(
                success=True,
                message="제안서 파싱 완료",
                document=document,
                total_sections=len(document.sections),
                total_pages=document.metadata.total_pages or 0,
            )
            
        except Exception as e:
            return ProposalParsingResponse(
                success=False,
                message=f"제안서 파싱 실패: {str(e)}",
                document=None,
                total_sections=0,
                total_pages=0,
            )
    
    def get_section_by_type(
        self,
        document: ProposalDocument,
        section_type: str
    ) -> List[ProposalSection]:
        """특정 타입의 섹션을 조회합니다.
        
        Args:
            document: 제안서 문서
            section_type: 섹션 타입
            
        Returns:
            섹션 리스트
        """
        return [
            section for section in document.sections
            if section.type.value == section_type
        ]
    
    def search_sections(
        self,
        document: ProposalDocument,
        keyword: str
    ) -> List[ProposalSection]:
        """키워드로 섹션을 검색합니다.
        
        Args:
            document: 제안서 문서
            keyword: 검색 키워드
            
        Returns:
            검색된 섹션 리스트
        """
        keyword_lower = keyword.lower()
        results = []
        
        for section in document.sections:
            if (keyword_lower in section.title.lower() or
                keyword_lower in section.content.lower()):
                results.append(section)
        
        return results
    
    def get_executive_summary(
        self,
        document: ProposalDocument
    ) -> Optional[ProposalSection]:
        """요약본을 조회합니다.
        
        Args:
            document: 제안서 문서
            
        Returns:
            요약본 섹션 또는 None
        """
        summaries = self.get_section_by_type(document, "executive_summary")
        return summaries[0] if summaries else None
    
    def get_budget_section(
        self,
        document: ProposalDocument
    ) -> Optional[ProposalSection]:
        """예산 섹션을 조회합니다.
        
        Args:
            document: 제안서 문서
            
        Returns:
            예산 섹션 또는 None
        """
        budgets = self.get_section_by_type(document, "budget")
        return budgets[0] if budgets else None
    
    def get_timeline_section(
        self,
        document: ProposalDocument
    ) -> Optional[ProposalSection]:
        """일정 섹션을 조회합니다.
        
        Args:
            document: 제안서 문서
            
        Returns:
            일정 섹션 또는 None
        """
        timelines = self.get_section_by_type(document, "timeline")
        return timelines[0] if timelines else None
