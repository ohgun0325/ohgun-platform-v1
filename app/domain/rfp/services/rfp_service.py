"""RfP 서비스.

RfP 문서 처리의 비즈니스 로직을 담당합니다.
"""

from __future__ import annotations

from pathlib import Path
from typing import Union, Optional, List

from app.domain.rfp.schemas.rfp_schema import (
    RfPDocument,
    Requirement,
    RequirementExtractionRequest,
    RequirementExtractionResponse,
)
from app.domain.rfp.parsers.rfp_pdf_parser import RfPPDFParser
from app.domain.rfp.parsers.requirement_extractor import RequirementExtractor
from app.domain.rfp.repositories.requirement_repository import (
    RequirementRepository,
    RfPDocumentRepository,
)


class RfPService:
    """RfP 서비스."""
    
    def __init__(
        self,
        requirement_repo: Optional[RequirementRepository] = None,
        document_repo: Optional[RfPDocumentRepository] = None,
    ):
        """
        Args:
            requirement_repo: 요구사항 저장소
            document_repo: 문서 저장소
        """
        self.requirement_repo = requirement_repo or RequirementRepository()
        self.document_repo = document_repo or RfPDocumentRepository()
        self.pdf_parser = RfPPDFParser(use_pdfplumber=True)
        self.requirement_extractor = RequirementExtractor()
    
    def process_rfp_pdf(
        self,
        pdf_source: Union[str, Path, bytes],
        save_to_repo: bool = True,
    ) -> RequirementExtractionResponse:
        """RfP PDF를 처리합니다.
        
        Args:
            pdf_source: PDF 파일 경로 또는 바이트 데이터
            save_to_repo: 저장소에 저장 여부
            
        Returns:
            추출 응답
        """
        try:
            # PDF 파싱
            document = self.pdf_parser.parse(pdf_source)
            
            # 저장소에 저장
            if save_to_repo:
                self.document_repo.save_document(document)
                self.requirement_repo.save_requirements(
                    document.requirements,
                    document.metadata.rfp_id,
                    overwrite=True
                )
            
            # 통계 계산
            mandatory_count = sum(
                1 for r in document.requirements 
                if r.priority.value == "mandatory"
            )
            
            return RequirementExtractionResponse(
                success=True,
                message="RfP 문서 처리 완료",
                document=document,
                total_requirements=len(document.requirements),
                mandatory_count=mandatory_count,
            )
            
        except Exception as e:
            return RequirementExtractionResponse(
                success=False,
                message=f"RfP 문서 처리 실패: {str(e)}",
                document=None,
                total_requirements=0,
                mandatory_count=0,
            )
    
    def get_rfp_document(self, rfp_id: str) -> Optional[RfPDocument]:
        """RfP 문서를 조회합니다.
        
        Args:
            rfp_id: RfP ID
            
        Returns:
            RfP 문서 또는 None
        """
        return self.document_repo.load_document(rfp_id)
    
    def get_requirements(self, rfp_id: str) -> List[Requirement]:
        """RfP의 요구사항을 조회합니다.
        
        Args:
            rfp_id: RfP ID
            
        Returns:
            요구사항 리스트
        """
        return self.requirement_repo.load_requirements(rfp_id)
    
    def search_requirements(
        self,
        rfp_id: str,
        keyword: str,
    ) -> List[Requirement]:
        """요구사항을 검색합니다.
        
        Args:
            rfp_id: RfP ID
            keyword: 검색 키워드
            
        Returns:
            검색된 요구사항 리스트
        """
        return self.requirement_repo.search_requirements(rfp_id, keyword)
    
    def get_mandatory_requirements(self, rfp_id: str) -> List[Requirement]:
        """필수 요구사항만 조회합니다.
        
        Args:
            rfp_id: RfP ID
            
        Returns:
            필수 요구사항 리스트
        """
        from app.domain.rfp.schemas.rfp_schema import RequirementPriority
        return self.requirement_repo.find_requirements_by_priority(
            rfp_id, 
            RequirementPriority.MANDATORY
        )
    
    def get_technical_requirements(self, rfp_id: str) -> List[Requirement]:
        """기술 요구사항만 조회합니다.
        
        Args:
            rfp_id: RfP ID
            
        Returns:
            기술 요구사항 리스트
        """
        from app.domain.rfp.schemas.rfp_schema import RequirementType
        return self.requirement_repo.find_requirements_by_type(
            rfp_id,
            RequirementType.TECHNICAL
        )
    
    def get_statistics(self, rfp_id: str) -> dict:
        """RfP 통계를 조회합니다.
        
        Args:
            rfp_id: RfP ID
            
        Returns:
            통계 딕셔너리
        """
        return self.requirement_repo.get_statistics(rfp_id)
    
    def list_all_rfps(self) -> List[str]:
        """저장된 모든 RfP ID를 조회합니다.
        
        Returns:
            RfP ID 리스트
        """
        return self.document_repo.list_documents()
