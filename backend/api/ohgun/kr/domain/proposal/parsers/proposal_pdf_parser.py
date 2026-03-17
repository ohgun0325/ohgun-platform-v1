"""제안서 PDF 파서.

PDF에서 제안서를 파싱하여 구조화된 데이터로 변환합니다.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Union, List, Dict, Any, Optional

from domain.shared.pdf import PDFContext, PDFFactory
from domain.proposal.schemas.proposal_schema import (
    ProposalDocument,
    ProposalMetadata,
    ProposalSection,
    SectionType,
    TableOfContents,
    TOCEntry,
)


class ProposalPDFParser:
    """제안서 PDF 파서."""
    
    def __init__(self, use_pdfplumber: bool = True):
        """
        Args:
            use_pdfplumber: True면 pdfplumber 사용, False면 PyMuPDF 사용
        """
        self.use_pdfplumber = use_pdfplumber
    
    def parse(self, pdf_source: Union[str, Path, bytes]) -> ProposalDocument:
        """제안서 PDF를 파싱합니다.
        
        Args:
            pdf_source: PDF 파일 경로 또는 바이트 데이터
            
        Returns:
            파싱된 제안서 문서
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
        
        # 목차 추출
        toc = self._extract_toc(raw_text, pages_data)
        
        # 섹션 추출
        sections = self._extract_sections(raw_text, pages_data, toc)
        
        return ProposalDocument(
            metadata=metadata,
            toc=toc,
            sections=sections,
            raw_text=raw_text,
        )
    
    def _extract_metadata(
        self,
        raw_text: str,
        pages_data: List[Dict[str, Any]]
    ) -> ProposalMetadata:
        """메타데이터를 추출합니다."""
        
        # 제목 추출
        title = self._extract_title(raw_text)
        
        # 조직명 추출
        organization = self._extract_organization(raw_text)
        
        # Proposal ID 추출
        proposal_id = self._extract_proposal_id(raw_text)
        
        return ProposalMetadata(
            proposal_id=proposal_id or "UNKNOWN",
            title=title or "제목 없음",
            organization=organization or "미상",
            total_pages=len(pages_data),
            version="1.0",
        )
    
    def _extract_title(self, text: str) -> Optional[str]:
        """제목을 추출합니다."""
        lines = text.split("\n")
        
        # 제안서 관련 키워드가 있는 줄 찾기
        for idx, line in enumerate(lines[:20]):
            line = line.strip()
            if any(keyword in line for keyword in ["제안서", "Proposal", "제안"]):
                if len(line) > 5 and len(line) < 200:
                    return line
        
        # 첫 번째 긴 줄
        for line in lines[:10]:
            line = line.strip()
            if len(line) > 10 and len(line) < 200:
                return line
        
        return None
    
    def _extract_organization(self, text: str) -> Optional[str]:
        """조직명을 추출합니다."""
        patterns = [
            r"제안\s*기관\s*[:：]\s*(.+)",
            r"제안\s*회사\s*[:：]\s*(.+)",
            r"제안자\s*[:：]\s*(.+)",
            r"Organization\s*[:：]\s*(.+)",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                org = match.group(1).strip()
                org = org.split("\n")[0].strip()
                if org:
                    return org
        
        return None
    
    def _extract_proposal_id(self, text: str) -> Optional[str]:
        """Proposal ID를 추출합니다."""
        patterns = [
            r"제안서\s*번호\s*[:：]\s*([A-Z0-9\-]+)",
            r"Proposal\s*No\.?\s*[:：]?\s*([A-Z0-9\-]+)",
            r"문서\s*번호\s*[:：]\s*([A-Z0-9\-]+)",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None
    
    def _extract_toc(
        self,
        raw_text: str,
        pages_data: List[Dict[str, Any]]
    ) -> Optional[TableOfContents]:
        """목차를 추출합니다."""
        
        # 목차 섹션 찾기
        toc_section = self._find_toc_section(raw_text)
        
        if not toc_section:
            return None
        
        # 목차 항목 추출
        entries = self._parse_toc_entries(toc_section)
        
        if not entries:
            return None
        
        return TableOfContents(entries=entries)
    
    def _find_toc_section(self, text: str) -> Optional[str]:
        """목차 섹션을 찾습니다."""
        lines = text.split("\n")
        
        # 목차 시작 찾기
        toc_start = -1
        for idx, line in enumerate(lines):
            if any(keyword in line for keyword in ["목차", "Contents", "Table of Contents", "차례"]):
                toc_start = idx
                break
        
        if toc_start == -1:
            return None
        
        # 목차 끝 찾기 (다음 섹션 시작)
        toc_end = len(lines)
        for idx in range(toc_start + 1, min(toc_start + 100, len(lines))):
            line = lines[idx].strip()
            # 본문 시작으로 보이는 패턴
            if re.match(r"^[I1일]\.\s+", line) and len(line) > 20:
                toc_end = idx
                break
        
        return "\n".join(lines[toc_start:toc_end])
    
    def _parse_toc_entries(self, toc_section: str) -> List[TOCEntry]:
        """목차 항목을 파싱합니다."""
        entries = []
        lines = toc_section.split("\n")
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 패턴: "1. 서론 ... 3" 또는 "1.1 배경 ... 5"
            match = re.match(r"^([\d\.]+)\s+(.+?)\s+\.{2,}\s*(\d+)$", line)
            if match:
                number, title, page = match.groups()
                level = number.count(".")
                if level == 0:
                    level = 1
                
                entries.append(TOCEntry(
                    title=f"{number} {title.strip()}",
                    page=int(page),
                    level=level
                ))
                continue
            
            # 패턴: "1. 서론 3" (점선 없이)
            match = re.match(r"^([\d\.]+)\s+(.+?)\s+(\d+)$", line)
            if match:
                number, title, page = match.groups()
                level = number.count(".")
                if level == 0:
                    level = 1
                
                entries.append(TOCEntry(
                    title=f"{number} {title.strip()}",
                    page=int(page),
                    level=level
                ))
        
        return entries
    
    def _extract_sections(
        self,
        raw_text: str,
        pages_data: List[Dict[str, Any]],
        toc: Optional[TableOfContents]
    ) -> List[ProposalSection]:
        """섹션을 추출합니다."""
        
        if not toc or not toc.entries:
            # 목차가 없으면 단순 분리
            return self._extract_sections_without_toc(raw_text, pages_data)
        
        sections = []
        lines = raw_text.split("\n")
        
        for idx, entry in enumerate(toc.entries):
            # 다음 섹션의 시작 찾기
            next_entry = toc.entries[idx + 1] if idx + 1 < len(toc.entries) else None
            
            # 섹션 내용 추출
            section_text = self._extract_section_content(
                lines,
                entry.title,
                next_entry.title if next_entry else None
            )
            
            # 섹션 타입 판단
            section_type = self._determine_section_type(entry.title)
            
            section = ProposalSection(
                id=f"SEC-{idx + 1:03d}",
                type=section_type,
                title=entry.title,
                level=entry.level,
                content=section_text,
                page_start=entry.page,
                page_end=next_entry.page - 1 if next_entry else None,
            )
            
            sections.append(section)
        
        return sections
    
    def _extract_sections_without_toc(
        self,
        raw_text: str,
        pages_data: List[Dict[str, Any]]
    ) -> List[ProposalSection]:
        """목차 없이 섹션을 추출합니다."""
        sections = []
        
        # 간단한 섹션 분리 (숫자로 시작하는 헤더)
        lines = raw_text.split("\n")
        current_section = []
        current_title = None
        section_idx = 0
        
        for line in lines:
            line_stripped = line.strip()
            
            # 섹션 헤더 패턴
            if re.match(r"^[\d\.]+\s+[^\d]", line_stripped) and len(line_stripped) < 100:
                if current_section and current_title:
                    section_idx += 1
                    sections.append(ProposalSection(
                        id=f"SEC-{section_idx:03d}",
                        type=SectionType.OTHER,
                        title=current_title,
                        level=1,
                        content="\n".join(current_section),
                    ))
                
                current_title = line_stripped
                current_section = []
            elif current_title:
                current_section.append(line)
        
        # 마지막 섹션
        if current_section and current_title:
            section_idx += 1
            sections.append(ProposalSection(
                id=f"SEC-{section_idx:03d}",
                type=SectionType.OTHER,
                title=current_title,
                level=1,
                content="\n".join(current_section),
            ))
        
        return sections
    
    def _extract_section_content(
        self,
        lines: List[str],
        section_title: str,
        next_section_title: Optional[str]
    ) -> str:
        """특정 섹션의 내용을 추출합니다."""
        
        # 섹션 시작 찾기
        start_idx = -1
        for idx, line in enumerate(lines):
            if section_title in line:
                start_idx = idx + 1
                break
        
        if start_idx == -1:
            return ""
        
        # 섹션 끝 찾기
        end_idx = len(lines)
        if next_section_title:
            for idx in range(start_idx, len(lines)):
                if next_section_title in lines[idx]:
                    end_idx = idx
                    break
        
        return "\n".join(lines[start_idx:end_idx]).strip()
    
    def _determine_section_type(self, title: str) -> SectionType:
        """제목에서 섹션 타입을 판단합니다."""
        title_lower = title.lower()
        
        if any(k in title_lower for k in ["목차", "contents"]):
            return SectionType.TOC
        elif any(k in title_lower for k in ["요약", "executive", "summary"]):
            return SectionType.EXECUTIVE_SUMMARY
        elif any(k in title_lower for k in ["서론", "introduction", "개요"]):
            return SectionType.INTRODUCTION
        elif any(k in title_lower for k in ["배경", "background"]):
            return SectionType.BACKGROUND
        elif any(k in title_lower for k in ["목표", "목적", "objectives"]):
            return SectionType.OBJECTIVES
        elif any(k in title_lower for k in ["접근", "approach", "방안"]):
            return SectionType.APPROACH
        elif any(k in title_lower for k in ["방법", "methodology"]):
            return SectionType.METHODOLOGY
        elif any(k in title_lower for k in ["일정", "timeline", "schedule"]):
            return SectionType.TIMELINE
        elif any(k in title_lower for k in ["예산", "budget", "비용"]):
            return SectionType.BUDGET
        elif any(k in title_lower for k in ["팀", "team", "인력", "조직"]):
            return SectionType.TEAM
        elif any(k in title_lower for k in ["자격", "qualifications", "경력"]):
            return SectionType.QUALIFICATIONS
        elif any(k in title_lower for k in ["참고", "references", "참조"]):
            return SectionType.REFERENCES
        elif any(k in title_lower for k in ["부록", "appendix", "첨부"]):
            return SectionType.APPENDIX
        else:
            return SectionType.OTHER
