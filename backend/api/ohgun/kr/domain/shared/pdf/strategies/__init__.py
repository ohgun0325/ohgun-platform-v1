"""PDF 전략 패턴 구현.

두 가지 전략을 제공:
1. pdfplumber_strategy: 표 추출에 강점
2. pymupdf_strategy: 빠른 텍스트 추출 및 이미지 렌더링
"""

from domain.shared.pdf.strategies.pdf_strategy import PDFExtractionStrategy
from domain.shared.pdf.strategies.pdfplumber_strategy import (
    PDFPlumberStrategy,
    PDFPlumberTableExtractor,
)
from domain.shared.pdf.strategies.pymupdf_strategy import (
    PyMuPDFStrategy,
    PyMuPDFImageExtractor,
)

__all__ = [
    "PDFExtractionStrategy",
    "PDFPlumberStrategy",
    "PDFPlumberTableExtractor",
    "PyMuPDFStrategy",
    "PyMuPDFImageExtractor",
]
