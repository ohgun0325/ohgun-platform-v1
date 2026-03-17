"""PDF 처리를 위한 컨텍스트 관리자 및 팩토리.

사용 예시:
    # pdfplumber 사용 (표 추출)
    with PDFContext.create("pdfplumber") as pdf:
        text = pdf.extract("document.pdf")
        tables = pdf.extract_tables_from_page("document.pdf", 1)
    
    # PyMuPDF 사용 (빠른 텍스트 추출)
    with PDFContext.create("pymupdf") as pdf:
        text = pdf.extract("document.pdf")
        image = pdf.render_page_to_image("document.pdf", 1)
"""

from __future__ import annotations

from typing import Literal, Union
from pathlib import Path

from domain.shared.pdf.strategies import (
    PDFExtractionStrategy,
    PDFPlumberStrategy,
    PyMuPDFStrategy,
)


class PDFContext:
    """PDF 처리 컨텍스트 관리자."""
    
    def __init__(self, strategy: PDFExtractionStrategy):
        """
        Args:
            strategy: PDF 추출 전략
        """
        self.strategy = strategy
    
    def __enter__(self):
        return self.strategy
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        return False
    
    @classmethod
    def create(
        cls, 
        strategy_type: Literal["pdfplumber", "pymupdf"],
        **kwargs
    ) -> PDFContext:
        """PDF 처리 컨텍스트를 생성합니다.
        
        Args:
            strategy_type: 전략 타입 ("pdfplumber" 또는 "pymupdf")
            **kwargs: 전략별 추가 설정
                - pdfplumber: extract_tables, extract_images
                - pymupdf: extract_images
        
        Returns:
            PDFContext 인스턴스
        
        Examples:
            >>> with PDFContext.create("pdfplumber", extract_tables=True) as pdf:
            ...     text = pdf.extract("doc.pdf")
        """
        if strategy_type == "pdfplumber":
            strategy = PDFPlumberStrategy(**kwargs)
        elif strategy_type == "pymupdf":
            strategy = PyMuPDFStrategy(**kwargs)
        else:
            raise ValueError(
                f"지원하지 않는 전략: {strategy_type}. "
                "'pdfplumber' 또는 'pymupdf'를 사용하세요."
            )
        
        return cls(strategy)


class PDFFactory:
    """PDF 전략 팩토리 (컨텍스트 관리자 없이 사용)."""
    
    @staticmethod
    def create_strategy(
        strategy_type: Literal["pdfplumber", "pymupdf"],
        **kwargs
    ) -> PDFExtractionStrategy:
        """PDF 추출 전략을 생성합니다.
        
        Args:
            strategy_type: 전략 타입
            **kwargs: 전략별 추가 설정
        
        Returns:
            PDFExtractionStrategy 인스턴스
        """
        if strategy_type == "pdfplumber":
            return PDFPlumberStrategy(**kwargs)
        elif strategy_type == "pymupdf":
            return PyMuPDFStrategy(**kwargs)
        else:
            raise ValueError(
                f"지원하지 않는 전략: {strategy_type}. "
                "'pdfplumber' 또는 'pymupdf'를 사용하세요."
            )
    
    @staticmethod
    def get_default_for_tables() -> PDFPlumberStrategy:
        """표 추출에 최적화된 기본 전략을 반환합니다."""
        return PDFPlumberStrategy(extract_tables=True)
    
    @staticmethod
    def get_default_for_text() -> PyMuPDFStrategy:
        """텍스트 추출에 최적화된 기본 전략을 반환합니다."""
        return PyMuPDFStrategy()
    
    @staticmethod
    def get_default_for_rendering() -> PyMuPDFStrategy:
        """이미지 렌더링에 최적화된 기본 전략을 반환합니다."""
        return PyMuPDFStrategy(extract_images=True)


def extract_pdf_text(
    pdf_path: Union[str, Path],
    strategy: Literal["pdfplumber", "pymupdf"] = "pymupdf"
) -> str:
    """PDF에서 텍스트를 추출하는 간단한 헬퍼 함수.
    
    Args:
        pdf_path: PDF 파일 경로
        strategy: 사용할 전략 (기본: "pymupdf")
    
    Returns:
        추출된 텍스트
    """
    pdf_strategy = PDFFactory.create_strategy(strategy)
    return pdf_strategy.extract(str(pdf_path))


def extract_pdf_tables(
    pdf_path: Union[str, Path],
    page_num: int
) -> list:
    """PDF에서 표를 추출하는 간단한 헬퍼 함수.
    
    Args:
        pdf_path: PDF 파일 경로
        page_num: 페이지 번호 (1-based)
    
    Returns:
        표 리스트
    """
    strategy = PDFPlumberStrategy(extract_tables=True)
    return strategy.extract_tables_from_page(pdf_path, page_num)
