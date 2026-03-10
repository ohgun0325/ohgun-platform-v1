"""pdfplumber 기반 PDF 추출 전략.

- 표(Table) 추출
- 텍스트 추출
- 페이지별 처리
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import List, Dict, Any, Union, Optional

try:
    import pdfplumber
except ImportError:
    raise ImportError("pdfplumber가 설치되지 않았습니다. pip install pdfplumber")

from app.domain.shared.pdf.strategies.pdf_strategy import PDFExtractionStrategy


class PDFPlumberStrategy(PDFExtractionStrategy):
    """pdfplumber를 사용한 PDF 추출 전략."""
    
    def __init__(self, extract_tables: bool = True, extract_images: bool = False):
        """
        Args:
            extract_tables: 표 추출 여부
            extract_images: 이미지 추출 여부 (기본: False)
        """
        self.extract_tables = extract_tables
        self.extract_images = extract_images
    
    def extract(self, file_path: str) -> str:
        """PDF에서 텍스트를 추출합니다.
        
        Args:
            file_path: PDF 파일 경로
            
        Returns:
            추출된 텍스트
        """
        pages_data = self.extract_pages(file_path)
        
        # 모든 페이지의 텍스트를 합침
        all_text = []
        for page_data in pages_data:
            all_text.append(page_data["text"])
            
            # 표가 있으면 추가
            if page_data["tables"]:
                all_text.append("\n[표 데이터]\n")
                for table in page_data["tables"]:
                    all_text.append(self._format_table(table))
        
        return "\n\n".join(all_text)
    
    def extract_pages(
        self, 
        pdf_source: Union[str, Path, bytes]
    ) -> List[Dict[str, Any]]:
        """PDF의 모든 페이지를 개별적으로 추출합니다.
        
        Args:
            pdf_source: PDF 파일 경로 또는 바이트 데이터
            
        Returns:
            페이지별 데이터 리스트. 각 페이지는 다음 구조:
            {
                "page_num": int,
                "text": str,
                "tables": List[List[List[str]]],
                "metadata": Dict
            }
        """
        pages_data = []
        
        # 파일 또는 바이트 스트림 열기
        if isinstance(pdf_source, bytes):
            pdf = pdfplumber.open(io.BytesIO(pdf_source))
        else:
            pdf = pdfplumber.open(pdf_source)
        
        try:
            for page_num, page in enumerate(pdf.pages, start=1):
                page_data = {
                    "page_num": page_num,
                    "text": "",
                    "tables": [],
                    "metadata": {
                        "width": page.width,
                        "height": page.height,
                    }
                }
                
                # 텍스트 추출
                text = page.extract_text()
                if text:
                    page_data["text"] = text
                
                # 표 추출
                if self.extract_tables:
                    tables = page.extract_tables()
                    if tables:
                        page_data["tables"] = tables
                
                pages_data.append(page_data)
                
        finally:
            pdf.close()
        
        return pages_data
    
    def extract_text_from_page(
        self, 
        pdf_source: Union[str, Path, bytes], 
        page_num: int
    ) -> str:
        """특정 페이지에서 텍스트만 추출합니다.
        
        Args:
            pdf_source: PDF 파일 경로 또는 바이트 데이터
            page_num: 페이지 번호 (1-based)
            
        Returns:
            추출된 텍스트
        """
        if isinstance(pdf_source, bytes):
            pdf = pdfplumber.open(io.BytesIO(pdf_source))
        else:
            pdf = pdfplumber.open(pdf_source)
        
        try:
            if page_num < 1 or page_num > len(pdf.pages):
                raise ValueError(f"페이지 번호 {page_num}이 범위를 벗어났습니다.")
            
            page = pdf.pages[page_num - 1]  # 0-based 인덱스
            text = page.extract_text()
            return text if text else ""
            
        finally:
            pdf.close()
    
    def extract_tables_from_page(
        self, 
        pdf_source: Union[str, Path, bytes], 
        page_num: int
    ) -> List[List[List[str]]]:
        """특정 페이지에서 표만 추출합니다.
        
        Args:
            pdf_source: PDF 파일 경로 또는 바이트 데이터
            page_num: 페이지 번호 (1-based)
            
        Returns:
            표 리스트 (각 표는 행들의 리스트)
        """
        if isinstance(pdf_source, bytes):
            pdf = pdfplumber.open(io.BytesIO(pdf_source))
        else:
            pdf = pdfplumber.open(pdf_source)
        
        try:
            if page_num < 1 or page_num > len(pdf.pages):
                raise ValueError(f"페이지 번호 {page_num}이 범위를 벗어났습니다.")
            
            page = pdf.pages[page_num - 1]
            tables = page.extract_tables()
            return tables if tables else []
            
        finally:
            pdf.close()
    
    def get_page_count(self, pdf_source: Union[str, Path, bytes]) -> int:
        """PDF의 총 페이지 수를 반환합니다.
        
        Args:
            pdf_source: PDF 파일 경로 또는 바이트 데이터
            
        Returns:
            페이지 수
        """
        if isinstance(pdf_source, bytes):
            pdf = pdfplumber.open(io.BytesIO(pdf_source))
        else:
            pdf = pdfplumber.open(pdf_source)
        
        try:
            return len(pdf.pages)
        finally:
            pdf.close()
    
    @staticmethod
    def _format_table(table: List[List[str]]) -> str:
        """표를 읽기 쉬운 텍스트 형식으로 변환합니다."""
        if not table:
            return ""
        
        lines = []
        for row in table:
            # None 값을 빈 문자열로 변환
            row_cleaned = [str(cell) if cell is not None else "" for cell in row]
            lines.append(" | ".join(row_cleaned))
        
        return "\n".join(lines)


class PDFPlumberTableExtractor:
    """표 추출에 특화된 pdfplumber 래퍼 클래스."""
    
    def __init__(self, table_settings: Optional[Dict[str, Any]] = None):
        """
        Args:
            table_settings: pdfplumber의 table extraction 설정
                예: {"vertical_strategy": "lines", "horizontal_strategy": "lines"}
        """
        self.table_settings = table_settings or {}
    
    def extract_tables_with_position(
        self, 
        pdf_source: Union[str, Path, bytes],
        page_num: int
    ) -> List[Dict[str, Any]]:
        """표를 위치 정보와 함께 추출합니다.
        
        Args:
            pdf_source: PDF 파일 경로 또는 바이트 데이터
            page_num: 페이지 번호 (1-based)
            
        Returns:
            표 정보 리스트. 각 항목은:
            {
                "data": List[List[str]],  # 표 데이터
                "bbox": (x0, y0, x1, y1),  # 바운딩 박스
                "rows": int,  # 행 수
                "cols": int   # 열 수
            }
        """
        if isinstance(pdf_source, bytes):
            pdf = pdfplumber.open(io.BytesIO(pdf_source))
        else:
            pdf = pdfplumber.open(pdf_source)
        
        try:
            if page_num < 1 or page_num > len(pdf.pages):
                raise ValueError(f"페이지 번호 {page_num}이 범위를 벗어났습니다.")
            
            page = pdf.pages[page_num - 1]
            tables_info = []
            
            # 표 찾기
            tables = page.find_tables(table_settings=self.table_settings)
            
            for table in tables:
                table_data = table.extract()
                if table_data:
                    tables_info.append({
                        "data": table_data,
                        "bbox": table.bbox,
                        "rows": len(table_data),
                        "cols": len(table_data[0]) if table_data else 0,
                    })
            
            return tables_info
            
        finally:
            pdf.close()
