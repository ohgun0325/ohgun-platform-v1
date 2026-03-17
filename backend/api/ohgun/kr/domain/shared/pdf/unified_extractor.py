"""통합 PDF Key-Value Extractor (Structured + Scanned PDF 지원).

이 모듈은 PyMuPDF와 EasyOCR을 통합하여 두 가지 유형의 PDF를 처리합니다:
1. Structured PDF: PyMuPDF로 직접 텍스트 추출 → Key-Value 매칭
2. Scanned PDF: PyMuPDF로 이미지 렌더링 → EasyOCR → Key-Value 매칭

핵심 기능:
- 자동 PDF 타입 감지 (텍스트 있음 vs 스캔)
- 폴백 메커니즘 (PyMuPDF 실패 → EasyOCR)
- 통일된 인터페이스 및 결과 포맷
"""

from __future__ import annotations

import logging
from typing import Dict, Any, Optional, List, Tuple, Union, Callable
from pathlib import Path

try:
    import fitz  # PyMuPDF
except ImportError:
    raise ImportError("PyMuPDF가 설치되지 않았습니다: pip install PyMuPDF")

from domain.shared.pdf.key_value_extractor import (
    KeyValueExtractor,
    MultiKeywordExtractor,
    OCRKeyValueExtractor,
)

logger = logging.getLogger(__name__)


class PDFType:
    """PDF 타입."""
    STRUCTURED = "structured"  # 텍스트 기반 PDF
    SCANNED = "scanned"  # 스캔/이미지 기반 PDF
    MIXED = "mixed"  # 혼합형


class UnifiedKeyValueExtractor:
    """Structured와 Scanned PDF 모두 지원하는 통합 extractor.
    
    동작 흐름:
    1. PDF 타입 자동 감지
    2. Structured: PyMuPDF 직접 사용
    3. Scanned: PyMuPDF(렌더링) → EasyOCR → Key-Value 매칭
    4. 폴백: PyMuPDF 실패 시 자동으로 OCR 시도
    
    Example:
        >>> from domain.shared.ocr.easyocr_reader import EasyOCRReader
        >>> 
        >>> ocr_reader = EasyOCRReader(gpu=True)
        >>> extractor = UnifiedKeyValueExtractor(ocr_reader=ocr_reader)
        >>> 
        >>> fields = {
        ...     "name": {"keywords": ["성명", "이름"]},
        ...     "company": {"keywords": ["업체명", "회사명"]},
        ... }
        >>> 
        >>> result = extractor.extract("form.pdf", 1, fields)
        >>> print(result["pdf_type"])  # "structured" or "scanned"
        >>> print(result["fields"]["name"]["value"])  # "홍길동"
    """
    
    def __init__(
        self,
        ocr_reader: Optional[Any] = None,
        max_distance: float = 300.0,
        same_line_tolerance: float = 5.0,
        text_threshold: int = 50,
        force_ocr: bool = False,
    ):
        """
        Args:
            ocr_reader: EasyOCRReader 인스턴스 (스캔 PDF용)
            max_distance: Key-Value 최대 거리
            same_line_tolerance: 같은 줄 판단 허용 오차
            text_threshold: 텍스트 기반 PDF로 판단하는 최소 문자 수
            force_ocr: True면 모든 PDF를 OCR로 처리 (테스트용)
        """
        self.ocr_reader = ocr_reader
        self.max_distance = max_distance
        self.same_line_tolerance = same_line_tolerance
        self.text_threshold = text_threshold
        self.force_ocr = force_ocr
        
        # 전략별 extractor
        self.pymupdf_extractor = MultiKeywordExtractor(max_distance, same_line_tolerance)
        self.ocr_extractor = OCRKeyValueExtractor(max_distance, same_line_tolerance)
    
    def extract(
        self,
        pdf_path: str | Path,
        page_num: int,
        field_definitions: Dict[str, Dict[str, Any]],
        auto_fallback: bool = True,
    ) -> Dict[str, Any]:
        """PDF에서 Key-Value 추출 (자동 타입 감지 및 폴백).
        
        Args:
            pdf_path: PDF 파일 경로
            page_num: 페이지 번호 (1-based)
            field_definitions: 필드 정의
                {
                    "field_name": {
                        "keywords": ["키워드1", "키워드2"],
                        "post_process": Optional[Callable[[str], str]]
                    }
                }
            auto_fallback: True면 PyMuPDF 실패 시 자동으로 OCR 시도
        
        Returns:
            {
                "pdf_type": "structured" | "scanned" | "mixed",
                "extraction_method": "pymupdf" | "ocr",
                "fields": {
                    "field_name": {
                        "value": str,
                        "key": str,
                        "confidence": float,
                        "direction": str,
                        "distance": float,
                        "bbox": dict,
                    }
                },
                "metadata": {
                    "page_num": int,
                    "total_words": int,
                    "text_length": int,
                },
                "error": str | None,
            }
        """
        pdf_path = Path(pdf_path)
        
        if not pdf_path.exists():
            return self._error_result(f"PDF 파일을 찾을 수 없습니다: {pdf_path}")
        
        # 1. PDF 타입 감지
        if self.force_ocr:
            pdf_type = PDFType.SCANNED
            logger.info("[통합 Extractor] force_ocr=True → OCR 모드로 실행")
        else:
            pdf_type = self._detect_pdf_type(pdf_path, page_num)
        
        logger.info(
            "[통합 Extractor] PDF 타입: %s, 페이지: %d, 필드: %d개",
            pdf_type,
            page_num,
            len(field_definitions),
        )
        
        # 2. Structured PDF 처리
        if pdf_type == PDFType.STRUCTURED:
            try:
                result = self.pymupdf_extractor.extract_fields(
                    pdf_path, page_num, field_definitions
                )
                
                # 추출 성공 확인
                if result["fields"]:
                    return {
                        "pdf_type": pdf_type,
                        "extraction_method": "pymupdf",
                        "fields": result["fields"],
                        "metadata": {
                            "page_num": page_num,
                            "total_words": len(result.get("raw_words", [])),
                        },
                        "error": None,
                    }
                else:
                    logger.warning("[통합 Extractor] PyMuPDF로 필드 추출 실패 (빈 결과)")
                    if auto_fallback and self.ocr_reader:
                        logger.info("[통합 Extractor] OCR 폴백 시도...")
                        return self._extract_with_ocr(pdf_path, page_num, field_definitions)
            except Exception as e:
                logger.exception("[통합 Extractor] PyMuPDF 추출 중 오류: %s", e)
                if auto_fallback and self.ocr_reader:
                    logger.info("[통합 Extractor] OCR 폴백 시도...")
                    return self._extract_with_ocr(pdf_path, page_num, field_definitions)
                else:
                    return self._error_result(f"PyMuPDF 추출 실패: {e}")
        
        # 3. Scanned PDF 처리
        elif pdf_type == PDFType.SCANNED:
            if not self.ocr_reader:
                return self._error_result("OCR 리더가 제공되지 않았습니다. EasyOCRReader를 전달하세요.")
            
            return self._extract_with_ocr(pdf_path, page_num, field_definitions)
        
        # 4. Mixed PDF 처리 (구현 필요 시 확장)
        else:
            return self._error_result(f"지원하지 않는 PDF 타입: {pdf_type}")
    
    def _detect_pdf_type(self, pdf_path: Path, page_num: int) -> str:
        """PDF 타입 감지 (텍스트 기반 vs 스캔).
        
        휴리스틱:
        - 페이지에서 추출한 텍스트가 text_threshold 이상이면 structured
        - 아니면 scanned
        """
        try:
            doc = fitz.open(str(pdf_path))
            try:
                if page_num < 1 or page_num > len(doc):
                    logger.warning("[타입 감지] 페이지 범위 초과: %d", page_num)
                    return PDFType.SCANNED
                
                page = doc[page_num - 1]
                text = page.get_text().strip()
                
                text_length = len(text)
                logger.info("[타입 감지] 페이지 %d 텍스트 길이: %d자", page_num, text_length)
                
                if text_length >= self.text_threshold:
                    return PDFType.STRUCTURED
                else:
                    return PDFType.SCANNED
            finally:
                doc.close()
        except Exception as e:
            logger.exception("[타입 감지] 오류 발생: %s → SCANNED로 가정", e)
            return PDFType.SCANNED
    
    def _extract_with_ocr(
        self,
        pdf_path: Path,
        page_num: int,
        field_definitions: Dict[str, Dict[str, Any]],
    ) -> Dict[str, Any]:
        """OCR을 사용한 Key-Value 추출.
        
        흐름:
        1. PyMuPDF로 페이지를 이미지로 렌더링
        2. EasyOCR로 텍스트 및 bbox 추출
        3. OCRKeyValueExtractor로 Key-Value 매칭
        """
        try:
            # 1. PDF 페이지를 이미지로 렌더링
            doc = fitz.open(str(pdf_path))
            try:
                if page_num < 1 or page_num > len(doc):
                    return self._error_result(f"페이지 번호 {page_num}이 범위를 벗어났습니다.")
                
                page = doc[page_num - 1]
                mat = fitz.Matrix(2.0, 2.0)  # 2x 확대 (OCR 정확도 향상)
                pix = page.get_pixmap(matrix=mat, alpha=False)
                
                # PIL Image로 변환
                from PIL import Image
                if pix.alpha:
                    pix = fitz.Pixmap(fitz.csRGB, pix)
                img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
                
                logger.info("[OCR 추출] 페이지 %d를 이미지로 렌더링 완료 (크기: %dx%d)", 
                           page_num, pix.width, pix.height)
            finally:
                doc.close()
            
            # 2. EasyOCR로 텍스트 추출
            import numpy as np
            img_array = np.array(img)
            ocr_results = self.ocr_reader.reader.readtext(img_array)
            
            logger.info("[OCR 추출] EasyOCR 완료: %d개 항목 인식", len(ocr_results))
            
            # 3. OCR Key-Value 추출
            result = self.ocr_extractor.extract_fields_from_ocr(
                ocr_results, field_definitions, min_confidence=0.5
            )
            
            return {
                "pdf_type": PDFType.SCANNED,
                "extraction_method": "ocr",
                "fields": result["fields"],
                "metadata": {
                    "page_num": page_num,
                    "total_words": len(result.get("raw_words", [])),
                    "ocr_items": len(ocr_results),
                },
                "error": None,
            }
        
        except Exception as e:
            logger.exception("[OCR 추출] 오류 발생: %s", e)
            return self._error_result(f"OCR 추출 실패: {e}")
    
    def _error_result(self, error_msg: str) -> Dict[str, Any]:
        """오류 결과 생성."""
        return {
            "pdf_type": "unknown",
            "extraction_method": "none",
            "fields": {},
            "metadata": {},
            "error": error_msg,
        }


# ===========================
# 편의 함수
# ===========================

def extract_from_any_pdf(
    pdf_path: str | Path,
    page_num: int,
    field_definitions: Dict[str, Dict[str, Any]],
    ocr_reader: Optional[Any] = None,
) -> Dict[str, Any]:
    """모든 타입의 PDF에서 Key-Value 추출 (자동 타입 감지).
    
    Args:
        pdf_path: PDF 파일 경로
        page_num: 페이지 번호 (1-based)
        field_definitions: 필드 정의
        ocr_reader: EasyOCRReader 인스턴스 (스캔 PDF용, 없으면 structured만 지원)
    
    Returns:
        추출 결과 딕셔너리
    
    Example:
        >>> from domain.shared.ocr.easyocr_reader import EasyOCRReader
        >>> 
        >>> ocr = EasyOCRReader(gpu=True)
        >>> fields = {
        ...     "name": {
        ...         "keywords": ["성명", "이름", "Name"],
        ...         "post_process": lambda x: x.strip(),
        ...     },
        ...     "birth_date": {
        ...         "keywords": ["생년월일", "출생일", "Birth Date"],
        ...         "post_process": lambda x: x.replace(" ", ""),
        ...     },
        ...     "company": {
        ...         "keywords": ["업체명", "회사명", "발행회사명"],
        ...     },
        ... }
        >>> 
        >>> result = extract_from_any_pdf("form.pdf", 1, fields, ocr)
        >>> 
        >>> if not result["error"]:
        ...     print(f"PDF 타입: {result['pdf_type']}")
        ...     print(f"추출 방법: {result['extraction_method']}")
        ...     for field_name, data in result["fields"].items():
        ...         print(f"{field_name}: {data['value']} (신뢰도: {data['confidence']:.2f})")
    """
    extractor = UnifiedKeyValueExtractor(
        ocr_reader=ocr_reader,
        max_distance=300.0,
        same_line_tolerance=5.0,
    )
    
    return extractor.extract(pdf_path, page_num, field_definitions, auto_fallback=True)


def extract_simple_dict(
    pdf_path: str | Path,
    page_num: int,
    keywords: Dict[str, List[str]],
    ocr_reader: Optional[Any] = None,
) -> Dict[str, str]:
    """간단한 추출 (필드명 → 값만 반환).
    
    Args:
        pdf_path: PDF 파일 경로
        page_num: 페이지 번호
        keywords: {"field_name": ["keyword1", "keyword2"], ...}
        ocr_reader: EasyOCRReader (옵션)
    
    Returns:
        {"field_name": "value", ...}
    
    Example:
        >>> result = extract_simple_dict(
        ...     "form.pdf",
        ...     1,
        ...     {"name": ["성명"], "company": ["회사명"]},
        ... )
        >>> print(result["name"])  # "홍길동"
    """
    # 필드 정의 형식 변환
    field_defs = {
        field_name: {"keywords": kw_list}
        for field_name, kw_list in keywords.items()
    }
    
    result = extract_from_any_pdf(pdf_path, page_num, field_defs, ocr_reader)
    
    if result.get("error"):
        logger.error("[간단 추출] 오류: %s", result["error"])
        return {}
    
    return {
        field_name: data["value"]
        for field_name, data in result.get("fields", {}).items()
    }


# ===========================
# 성능 최적화 유틸리티
# ===========================

class BatchExtractor:
    """여러 페이지를 배치로 처리하여 성능 최적화.
    
    최적화 기법:
    - PDF 문서를 한 번만 열고 여러 페이지 처리
    - OCR 모델 재사용 (초기화 비용 절감)
    - 병렬 처리 옵션 (멀티프로세싱)
    """
    
    def __init__(
        self,
        extractor: UnifiedKeyValueExtractor,
    ):
        self.extractor = extractor
    
    def extract_multiple_pages(
        self,
        pdf_path: str | Path,
        pages: List[int],
        field_definitions: Dict[str, Dict[str, Any]],
        parallel: bool = False,
    ) -> Dict[int, Dict[str, Any]]:
        """여러 페이지에서 동시 추출.
        
        Args:
            pdf_path: PDF 파일 경로
            pages: 페이지 번호 리스트 (1-based)
            field_definitions: 필드 정의
            parallel: True면 병렬 처리 (멀티프로세싱)
        
        Returns:
            {page_num: extraction_result, ...}
        
        Example:
            >>> extractor = UnifiedKeyValueExtractor(ocr_reader=ocr)
            >>> batch = BatchExtractor(extractor)
            >>> results = batch.extract_multiple_pages(
            ...     "multi_page_form.pdf",
            ...     [1, 2, 3],
            ...     field_definitions,
            ... )
            >>> for page_num, result in results.items():
            ...     print(f"페이지 {page_num}: {result['fields']}")
        """
        if not parallel:
            # 순차 처리
            results = {}
            for page_num in pages:
                try:
                    result = self.extractor.extract(
                        pdf_path, page_num, field_definitions
                    )
                    results[page_num] = result
                except Exception as e:
                    logger.exception("[배치 추출] 페이지 %d 오류: %s", page_num, e)
                    results[page_num] = self.extractor._error_result(str(e))
            
            return results
        else:
            # 병렬 처리 (멀티프로세싱)
            return self._extract_parallel(pdf_path, pages, field_definitions)
    
    def _extract_parallel(
        self,
        pdf_path: Path,
        pages: List[int],
        field_definitions: Dict[str, Dict[str, Any]],
    ) -> Dict[int, Dict[str, Any]]:
        """병렬 추출 (멀티프로세싱).
        
        Note: OCR 모델은 pickle 불가능하므로 프로세스마다 재초기화 필요.
        """
        from concurrent.futures import ProcessPoolExecutor, as_completed
        
        results = {}
        
        with ProcessPoolExecutor(max_workers=4) as executor:
            futures = {
                executor.submit(
                    self._extract_single_page_worker,
                    str(pdf_path),
                    page_num,
                    field_definitions,
                ): page_num
                for page_num in pages
            }
            
            for future in as_completed(futures):
                page_num = futures[future]
                try:
                    result = future.result()
                    results[page_num] = result
                except Exception as e:
                    logger.exception("[병렬 추출] 페이지 %d 오류: %s", page_num, e)
                    results[page_num] = self.extractor._error_result(str(e))
        
        return results
    
    @staticmethod
    def _extract_single_page_worker(
        pdf_path: str,
        page_num: int,
        field_definitions: Dict[str, Dict[str, Any]],
    ) -> Dict[str, Any]:
        """워커 프로세스용 추출 함수 (OCR 없이 PyMuPDF만).
        
        멀티프로세싱에서는 OCR 모델 재초기화 비용이 크므로
        PyMuPDF만 사용하는 것이 권장됩니다.
        """
        extractor = MultiKeywordExtractor()
        result = extractor.extract_fields(pdf_path, page_num, field_definitions)
        
        return {
            "pdf_type": PDFType.STRUCTURED,
            "extraction_method": "pymupdf",
            "fields": result["fields"],
            "metadata": {
                "page_num": page_num,
                "total_words": len(result.get("raw_words", [])),
            },
            "error": None,
        }


# ===========================
# 고급 기능
# ===========================

class AdvancedExtractor:
    """고급 Key-Value 추출 기능.
    
    추가 기능:
    - 테이블 구조 자동 감지
    - 반복 패턴 추출 (동일 키가 여러 개 있는 경우)
    - 계층적 매칭 (섹션별 추출)
    """
    
    def __init__(self, base_extractor: UnifiedKeyValueExtractor):
        self.base_extractor = base_extractor
    
    def extract_repeated_fields(
        self,
        pdf_path: str | Path,
        page_num: int,
        field_keywords: List[str],
    ) -> List[str]:
        """동일한 키가 여러 번 나타나는 경우 모든 값 추출.
        
        예: "담당자" 필드가 3번 나타나고 각각 다른 값을 가짐
        
        Args:
            pdf_path: PDF 파일 경로
            page_num: 페이지 번호
            field_keywords: 찾을 키워드 리스트
        
        Returns:
            추출된 값 리스트
        
        Example:
            >>> extractor = AdvancedExtractor(unified_extractor)
            >>> values = extractor.extract_repeated_fields(
            ...     "team_list.pdf",
            ...     1,
            ...     ["담당자", "책임자"],
            ... )
            >>> print(values)  # ["홍길동", "김철수", "이영희"]
        """
        # PyMuPDF로 단어 추출
        doc = fitz.open(str(pdf_path))
        try:
            page = doc[page_num - 1]
            raw_words = page.get_text("words")
            
            from domain.shared.pdf.key_value_extractor import Word, BBox
            
            words = [
                Word(
                    text=item[4].strip(),
                    bbox=BBox(item[0], item[1], item[2], item[3]),
                    block_no=item[5],
                    line_no=item[6],
                    word_no=item[7],
                )
                for item in raw_words
                if item[4].strip()
            ]
        finally:
            doc.close()
        
        # 키워드 모두 찾기
        key_extractor = KeyValueExtractor()
        key_words = key_extractor._find_keywords(words, field_keywords)
        
        # 각 키워드에 대해 value 찾기
        values = []
        used_values = set()
        
        for key_word in key_words:
            candidates = key_extractor._find_value_candidates(key_word, words)
            
            if not candidates:
                continue
            
            # 최고 점수 후보 선택
            best_candidate = max(
                candidates,
                key=lambda c: key_extractor._calculate_score(
                    key_word.bbox, c["word"].bbox, c["direction"], c["distance"]
                )
            )
            
            value = best_candidate["word"].text
            
            # 중복 제거
            if value not in used_values:
                values.append(value)
                used_values.add(value)
        
        return values
    
    def extract_table_as_dict(
        self,
        pdf_path: str | Path,
        page_num: int,
        column_keywords: Dict[str, List[str]],
        min_rows: int = 1,
    ) -> List[Dict[str, str]]:
        """표 형태의 데이터를 행별로 추출.
        
        예:
        | 성명   | 생년월일   | 연락처        |
        |--------|-----------|--------------|
        | 홍길동 | 1990-01-01| 010-1234-5678|
        | 김철수 | 1985-05-15| 010-9876-5432|
        
        Args:
            pdf_path: PDF 파일 경로
            page_num: 페이지 번호
            column_keywords: 열 이름 → 키워드 매핑
            min_rows: 최소 행 수
        
        Returns:
            행별 딕셔너리 리스트
            [
                {"name": "홍길동", "birth": "1990-01-01", ...},
                {"name": "김철수", "birth": "1985-05-15", ...},
            ]
        
        Note:
            이 기능은 간단한 표에만 작동합니다.
            복잡한 표는 pdfplumber의 extract_tables 사용을 권장합니다.
        """
        # TODO: 표 구조 자동 감지 및 행별 추출
        # 현재는 기본 Key-Value 추출만 지원
        logger.warning("[표 추출] extract_table_as_dict는 아직 구현되지 않았습니다.")
        return []


# ===========================
# Production Best Practices
# ===========================

def create_production_extractor(
    enable_ocr: bool = True,
    gpu: bool = True,
) -> UnifiedKeyValueExtractor:
    """Production 환경용 extractor 생성.
    
    Args:
        enable_ocr: OCR 활성화 여부
        gpu: GPU 사용 여부 (OCR)
    
    Returns:
        설정된 UnifiedKeyValueExtractor
    
    Best Practices:
    1. 한 번 생성하여 재사용 (OCR 모델 초기화 비용 절감)
    2. GPU가 있으면 반드시 활성화 (OCR 속도 10배 이상 향상)
    3. 에러 핸들링 및 로깅 설정
    
    Example:
        >>> # 앱 시작 시 한 번 생성
        >>> extractor = create_production_extractor(enable_ocr=True, gpu=True)
        >>> 
        >>> # 요청마다 재사용
        >>> def process_pdf(pdf_path, page_num):
        ...     return extractor.extract(pdf_path, page_num, field_defs)
    """
    ocr_reader = None
    
    if enable_ocr:
        try:
            from domain.shared.ocr.easyocr_reader import EasyOCRReader
            ocr_reader = EasyOCRReader(languages=['ko', 'en'], gpu=gpu, verbose=False)
            logger.info("[Production Extractor] EasyOCR 초기화 완료 (GPU: %s)", gpu)
        except Exception as e:
            logger.exception("[Production Extractor] EasyOCR 초기화 실패: %s", e)
            logger.warning("[Production Extractor] OCR 없이 실행 (Structured PDF만 지원)")
    
    extractor = UnifiedKeyValueExtractor(
        ocr_reader=ocr_reader,
        max_distance=300.0,  # Production 권장값
        same_line_tolerance=5.0,
        text_threshold=50,
        force_ocr=False,
    )
    
    logger.info("[Production Extractor] 통합 Extractor 생성 완료")
    
    return extractor


# ===========================
# 필드 정의 템플릿
# ===========================

def get_standard_field_definitions() -> Dict[str, Dict[str, Any]]:
    """표준 문서 필드 정의 (한국 양식 기준).
    
    Returns:
        필드 정의 딕셔너리 (재사용 가능)
    """
    return {
        "name": {
            "keywords": ["성명", "이름", "담당자명", "담당자", "Name", "성 명"],
            "post_process": lambda x: x.strip(),
        },
        "birth_date": {
            "keywords": ["생년월일", "출생일", "생 년 월 일", "Birth Date", "DOB"],
            "post_process": lambda x: x.replace(" ", "").replace(".", "-"),
        },
        "company": {
            "keywords": ["업체명", "회사명", "발행회사명", "법인명", "회 사 명", "Company"],
            "post_process": lambda x: x.strip(),
        },
        "business_number": {
            "keywords": ["사업자번호", "사업자 번호", "사업자등록번호", "Business Number"],
            "post_process": lambda x: x.replace(" ", "").replace("-", ""),
        },
        "phone": {
            "keywords": ["연락처", "전화번호", "연 락 처", "Phone", "Tel"],
            "post_process": lambda x: x.replace(" ", ""),
        },
        "address": {
            "keywords": ["주소", "주 소", "소재지", "Address"],
            "post_process": lambda x: x.strip(),
        },
        "email": {
            "keywords": ["이메일", "이 메 일", "Email", "E-mail"],
            "post_process": lambda x: x.strip().lower(),
        },
        "date": {
            "keywords": ["작성일", "작성 일", "발행일", "날짜", "Date"],
            "post_process": lambda x: x.replace(" ", ""),
        },
    }


def get_koica_proposal_field_definitions() -> Dict[str, Dict[str, Any]]:
    """KOICA 제안서 특화 필드 정의.
    
    Returns:
        KOICA 양식용 필드 정의
    """
    return {
        "proposal_title": {
            "keywords": ["사업명", "사업 명", "제안서명", "프로젝트명"],
            "post_process": lambda x: x.strip(),
        },
        "proposer_name": {
            "keywords": ["제안기관", "제안 기관", "제안자", "제안회사"],
            "post_process": lambda x: x.strip(),
        },
        "project_period": {
            "keywords": ["사업기간", "사업 기간", "프로젝트 기간", "수행기간"],
            "post_process": lambda x: x.replace(" ", ""),
        },
        "total_budget": {
            "keywords": ["총 사업비", "총사업비", "예산", "사업비"],
            "post_process": lambda x: x.replace(",", "").replace(" ", ""),
        },
        "target_country": {
            "keywords": ["대상국가", "대상 국가", "협력국"],
            "post_process": lambda x: x.strip(),
        },
        "contact_person": {
            "keywords": ["담당자", "담당자명", "연락담당자"],
            "post_process": lambda x: x.strip(),
        },
        "contact_phone": {
            "keywords": ["담당자 연락처", "연락처", "전화번호"],
            "post_process": lambda x: x.replace(" ", ""),
        },
        "submission_date": {
            "keywords": ["제출일", "제출 일자", "작성일"],
            "post_process": lambda x: x.replace(" ", ""),
        },
    }
