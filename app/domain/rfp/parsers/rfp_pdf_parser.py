"""RfP PDF 파서.

PDF에서 RfP 문서를 파싱하여 구조화된 데이터로 변환합니다.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Union, List, Dict, Any, Optional

from app.domain.shared.pdf import PDFContext, PDFFactory
from app.domain.rfp.schemas.rfp_schema import (
    RfPDocument,
    RfPMetadata,
    Requirement,
    RequirementType,
    RequirementPriority,
)


class RfPPDFParser:
    """RfP PDF 문서 파서."""
    
    def __init__(self, use_pdfplumber: bool = True):
        """
        Args:
            use_pdfplumber: True면 pdfplumber 사용 (표 추출), False면 PyMuPDF 사용
        """
        self.use_pdfplumber = use_pdfplumber
        self.strategy_type = "pdfplumber" if use_pdfplumber else "pymupdf"
    
    def parse(self, pdf_source: Union[str, Path, bytes]) -> RfPDocument:
        """RfP PDF를 파싱합니다.
        
        Args:
            pdf_source: PDF 파일 경로 또는 바이트 데이터
            
        Returns:
            파싱된 RfP 문서
        """
        # PDF 전략 선택
        if self.use_pdfplumber:
            strategy = PDFFactory.get_default_for_tables()
        else:
            strategy = PDFFactory.get_default_for_text()
        
        # 전체 텍스트 추출
        raw_text = strategy.extract(str(pdf_source) if not isinstance(pdf_source, bytes) else pdf_source)
        
        # 페이지별 데이터 추출
        pages_data = strategy.extract_pages(pdf_source)
        
        # 메타데이터 추출
        metadata = self._extract_metadata(raw_text, pages_data)
        
        # 요구사항 추출 (기본 패턴 매칭)
        requirements = self._extract_requirements_basic(raw_text, pages_data)
        
        # 표 데이터 추출 (pdfplumber 사용 시)
        extracted_tables = None
        if self.use_pdfplumber:
            extracted_tables = self._extract_all_tables(pages_data)
        
        return RfPDocument(
            metadata=metadata,
            requirements=requirements,
            evaluation_criteria=[],  # 추후 구현
            raw_text=raw_text,
            extracted_tables=extracted_tables,
        )
    
    def _extract_metadata(
        self, 
        raw_text: str, 
        pages_data: List[Dict[str, Any]]
    ) -> RfPMetadata:
        """메타데이터를 추출합니다."""
        
        # 제목 추출 (첫 페이지의 큰 텍스트 또는 첫 줄)
        title = self._extract_title(raw_text)
        
        # 발주 기관 추출
        organization = self._extract_organization(raw_text)
        
        # RfP ID 추출
        rfp_id = self._extract_rfp_id(raw_text)
        
        return RfPMetadata(
            rfp_id=rfp_id or "UNKNOWN",
            title=title or "제목 없음",
            organization=organization or "미상",
            total_pages=len(pages_data),
            document_version="1.0",
        )
    
    def _extract_title(self, text: str) -> Optional[str]:
        """제목을 추출합니다."""
        lines = text.split("\n")
        for line in lines[:10]:  # 첫 10줄 내에서 찾기
            line = line.strip()
            if len(line) > 10 and len(line) < 200:
                # 제목처럼 보이는 줄
                if not line.startswith(("페이지", "Page", "목차", "Contents")):
                    return line
        return None
    
    def _extract_organization(self, text: str) -> Optional[str]:
        """발주 기관을 추출합니다."""
        # 패턴: "발주 기관:", "발주자:", "Organization:" 등
        patterns = [
            r"발주\s*기관\s*[:：]\s*(.+)",
            r"발주자\s*[:：]\s*(.+)",
            r"Organization\s*[:：]\s*(.+)",
            r"발주\s*[:：]\s*(.+)",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                org = match.group(1).strip()
                # 줄바꿈 전까지만
                org = org.split("\n")[0].strip()
                if org:
                    return org
        
        return None
    
    def _extract_rfp_id(self, text: str) -> Optional[str]:
        """RfP ID를 추출합니다."""
        # 패턴: "입찰번호:", "RFP No:", "공고번호:" 등
        patterns = [
            r"입찰\s*번호\s*[:：]\s*([A-Z0-9\-]+)",
            r"RFP\s*No\.?\s*[:：]?\s*([A-Z0-9\-]+)",
            r"공고\s*번호\s*[:：]\s*([A-Z0-9\-]+)",
            r"번호\s*[:：]\s*([A-Z0-9\-]+)",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None
    
    def _extract_requirements_basic(
        self, 
        raw_text: str, 
        pages_data: List[Dict[str, Any]]
    ) -> List[Requirement]:
        """기본 패턴 매칭으로 요구사항을 추출합니다.
        
        Note: 실제로는 LLM을 사용하는 것이 더 정확합니다.
        """
        requirements = []
        
        # 요구사항 섹션 찾기
        requirement_sections = self._find_requirement_sections(raw_text)
        
        for idx, section_text in enumerate(requirement_sections, start=1):
            # 간단한 요구사항 항목 추출
            items = self._extract_requirement_items(section_text)
            
            for item_idx, item_text in enumerate(items, start=1):
                req_id = f"REQ-{idx:03d}-{item_idx:02d}"
                
                # 우선순위 판단
                priority = self._determine_priority(item_text)
                
                # 타입 판단
                req_type = self._determine_type(item_text)
                
                requirement = Requirement(
                    id=req_id,
                    type=req_type,
                    priority=priority,
                    title=self._extract_requirement_title(item_text),
                    description=item_text,
                    keywords=self._extract_keywords(item_text),
                )
                
                requirements.append(requirement)
        
        return requirements
    
    def _find_requirement_sections(self, text: str) -> List[str]:
        """요구사항 섹션을 찾습니다."""
        sections = []
        
        # 요구사항 관련 헤더 패턴
        headers = [
            "요구사항", "요구 사항", "Requirements",
            "기술 요구사항", "기능 요구사항", "Technical Requirements",
            "제안 요구사항", "Proposal Requirements",
        ]
        
        lines = text.split("\n")
        current_section = []
        in_requirement_section = False
        
        for line in lines:
            line_stripped = line.strip()
            
            # 헤더 발견
            if any(header in line_stripped for header in headers):
                if current_section:
                    sections.append("\n".join(current_section))
                current_section = [line]
                in_requirement_section = True
                continue
            
            # 새로운 섹션 시작 (번호가 있는 헤더)
            if re.match(r"^\d+\.", line_stripped) and len(line_stripped) < 100:
                if current_section and in_requirement_section:
                    sections.append("\n".join(current_section))
                current_section = []
                in_requirement_section = False
            
            if in_requirement_section and line_stripped:
                current_section.append(line)
        
        if current_section:
            sections.append("\n".join(current_section))
        
        return sections
    
    def _extract_requirement_items(self, section_text: str) -> List[str]:
        """섹션에서 개별 요구사항 항목을 추출합니다."""
        items = []
        
        # 패턴: 번호나 불릿으로 시작하는 항목
        lines = section_text.split("\n")
        current_item = []
        
        for line in lines:
            line_stripped = line.strip()
            
            # 새로운 항목 시작
            if re.match(r"^[\d\-•▪◦○]\s*\.?\s+", line_stripped):
                if current_item:
                    items.append("\n".join(current_item))
                current_item = [line_stripped]
            elif current_item and line_stripped:
                current_item.append(line_stripped)
        
        if current_item:
            items.append("\n".join(current_item))
        
        return items
    
    def _determine_priority(self, text: str) -> RequirementPriority:
        """텍스트에서 우선순위를 판단합니다."""
        text_lower = text.lower()
        
        if any(keyword in text_lower for keyword in ["필수", "mandatory", "required", "must"]):
            return RequirementPriority.MANDATORY
        elif any(keyword in text_lower for keyword in ["강력", "highly", "recommended"]):
            return RequirementPriority.HIGHLY_DESIRABLE
        elif any(keyword in text_lower for keyword in ["권장", "desirable", "should"]):
            return RequirementPriority.DESIRABLE
        else:
            return RequirementPriority.OPTIONAL
    
    def _determine_type(self, text: str) -> RequirementType:
        """텍스트에서 요구사항 타입을 판단합니다."""
        text_lower = text.lower()
        
        if any(keyword in text_lower for keyword in ["기술", "technical", "아키텍처", "architecture"]):
            return RequirementType.TECHNICAL
        elif any(keyword in text_lower for keyword in ["기능", "functional", "function"]):
            return RequirementType.FUNCTIONAL
        elif any(keyword in text_lower for keyword in ["조직", "organizational", "team"]):
            return RequirementType.ORGANIZATIONAL
        elif any(keyword in text_lower for keyword in ["재무", "financial", "budget", "예산"]):
            return RequirementType.FINANCIAL
        elif any(keyword in text_lower for keyword in ["법", "legal", "규정", "compliance"]):
            return RequirementType.LEGAL
        else:
            return RequirementType.OTHER
    
    def _extract_requirement_title(self, text: str) -> str:
        """요구사항 제목을 추출합니다 (첫 문장)."""
        # 첫 줄 또는 첫 문장
        lines = text.split("\n")
        first_line = lines[0] if lines else text
        
        # 번호 제거
        first_line = re.sub(r"^[\d\-•▪◦○]\s*\.?\s+", "", first_line)
        
        # 최대 100자
        if len(first_line) > 100:
            first_line = first_line[:97] + "..."
        
        return first_line.strip()
    
    def _extract_keywords(self, text: str) -> List[str]:
        """키워드를 추출합니다 (간단한 버전)."""
        # 실제로는 NLP나 LLM을 사용하는 것이 좋습니다
        keywords = []
        
        # 대문자로 시작하는 중요 단어
        words = re.findall(r"\b[A-Z][a-z]+\b", text)
        keywords.extend(words[:5])
        
        # 기술 관련 키워드
        tech_keywords = ["AI", "ML", "클라우드", "AWS", "Azure", "API", "데이터베이스", "보안"]
        for keyword in tech_keywords:
            if keyword in text:
                keywords.append(keyword)
        
        return list(set(keywords))[:10]  # 중복 제거 및 최대 10개
    
    def _extract_all_tables(self, pages_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """모든 페이지에서 표를 추출합니다."""
        all_tables = []
        
        for page_data in pages_data:
            page_num = page_data.get("page_num", 0)
            tables = page_data.get("tables", [])
            
            for table_idx, table in enumerate(tables, start=1):
                all_tables.append({
                    "page_num": page_num,
                    "table_idx": table_idx,
                    "data": table,
                    "rows": len(table),
                    "cols": len(table[0]) if table else 0,
                })
        
        return all_tables
