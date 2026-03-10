"""PDF 처리 모듈.

전략 패턴을 사용하여 다양한 PDF 라이브러리를 지원합니다.

사용 예시:
    # 간단한 텍스트 추출
    from app.domain.shared.pdf import extract_pdf_text
    text = extract_pdf_text("document.pdf")
    
    # 표 추출
    from app.domain.shared.pdf import extract_pdf_tables
    tables = extract_pdf_tables("document.pdf", page_num=1)
    
    # 컨텍스트 관리자 사용
    from app.domain.shared.pdf import PDFContext
    with PDFContext.create("pdfplumber") as pdf:
        pages = pdf.extract_pages("document.pdf")
"""

from app.domain.shared.pdf.strategies import (
    PDFExtractionStrategy,
    PDFPlumberStrategy,
    PDFPlumberTableExtractor,
    PyMuPDFStrategy,
    PyMuPDFImageExtractor,
)

from app.domain.shared.pdf.pdf_context import (
    PDFContext,
    PDFFactory,
    extract_pdf_text,
    extract_pdf_tables,
)

from app.domain.shared.pdf.key_value_extractor import (
    KeyValueExtractor,
    MultiKeywordExtractor,
    OCRKeyValueExtractor,
    BBox,
    Word,
    KeyValuePair,
    Direction,
    extract_simple,
    extract_with_details,
    extract_from_ocr_simple,
)

from app.domain.shared.pdf.unified_extractor import (
    UnifiedKeyValueExtractor,
    BatchExtractor,
    AdvancedExtractor,
    extract_from_any_pdf,
    extract_simple_dict,
    create_production_extractor,
    get_standard_field_definitions,
    get_koica_proposal_field_definitions,
)

__all__ = [
    # 전략 패턴
    "PDFExtractionStrategy",
    "PDFPlumberStrategy",
    "PDFPlumberTableExtractor",
    "PyMuPDFStrategy",
    "PyMuPDFImageExtractor",
    # 컨텍스트 및 팩토리
    "PDFContext",
    "PDFFactory",
    # 헬퍼 함수
    "extract_pdf_text",
    "extract_pdf_tables",
    # Key-Value 추출
    "KeyValueExtractor",
    "MultiKeywordExtractor",
    "OCRKeyValueExtractor",
    "UnifiedKeyValueExtractor",
    "BatchExtractor",
    "AdvancedExtractor",
    # 데이터 클래스
    "BBox",
    "Word",
    "KeyValuePair",
    "Direction",
    # 편의 함수
    "extract_simple",
    "extract_with_details",
    "extract_from_ocr_simple",
    "extract_from_any_pdf",
    "extract_simple_dict",
    "create_production_extractor",
    "get_standard_field_definitions",
    "get_koica_proposal_field_definitions",
]
