"""Excel에서 Key-Value 필드를 자동으로 추출하는 모듈.

OCR 파이프라인과 유사하게, Excel 시트에서:
- 키워드 기반 필드 매핑 (1차: 문자열 매칭)
- 임베딩 기반 의미 매칭 (2차: semantic matching)
- 템플릿 자동완성용 필드 추출

지원 레이아웃:
1. 수직 레이아웃: A열에 라벨, B열에 값
   예: A2="회사명", B2="삼성 SDI"
2. 수평 레이아웃: 첫 행에 라벨, 다음 행에 값
   예: A1="회사명", A2="삼성 SDI"
3. 자유 형식: 키워드와 값이 같은 행/열에 인접
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import pandas as pd

from domain.shared.bases.semantic_matcher import get_default_semantic_matcher
from domain.shared.ms_excel.excel_reader import PandasExcelReader

logger = logging.getLogger(__name__)


class ExcelFieldExtractor:
    """Excel 시트에서 필드를 자동으로 추출하는 클래스.
    
    동작 방식:
    1. 시트를 pandas DataFrame으로 읽기
    2. 각 필드에 대해 키워드 찾기 (문자열 기반)
    3. 실패 시 임베딩 기반 의미 매칭으로 폴백
    4. 키워드 주변의 값을 추출
    """
    
    def __init__(
        self,
        use_semantic_matching: bool = True,
        semantic_threshold: float = 0.75,
    ):
        """
        Args:
            use_semantic_matching: 임베딩 기반 매칭 사용 여부
            semantic_threshold: 의미 매칭 최소 유사도 (0.0~1.0)
        """
        self.use_semantic_matching = use_semantic_matching
        self.semantic_threshold = semantic_threshold
        self._semantic_matcher = None
    
    def extract_fields(
        self,
        excel_path: Union[str, Path],
        field_definitions: Dict[str, Dict[str, Any]],
        sheet_name: Optional[Union[str, int]] = None,
    ) -> Dict[str, Any]:
        """Excel 파일에서 필드를 추출합니다.
        
        Args:
            excel_path: Excel 파일 경로
            field_definitions: 필드 정의
                {
                    "field_name": {
                        "keywords": ["키워드1", "키워드2"],
                        "post_process": Optional[Callable[[str], str]]
                    }
                }
            sheet_name: 시트 이름 또는 인덱스 (None이면 첫 시트)
        
        Returns:
            {
                "fields": {
                    "field_name": {
                        "value": str,
                        "matched_keyword": str,
                        "confidence": float,
                        "location": {"row": int, "col": int},
                    }
                },
                "metadata": {
                    "sheet_name": str,
                    "row_count": int,
                    "col_count": int,
                },
                "error": str | None,
            }
        """
        try:
            # 1. Excel 읽기 (한 곳: PandasExcelReader)
            reader = PandasExcelReader()
            df = reader.read_dataframe(excel_path, sheet_name=sheet_name)
            sheet_names = reader.get_sheet_names(excel_path)
            name_or_idx = sheet_name if sheet_name is not None else 0
            actual_sheet_name = (
                name_or_idx if isinstance(name_or_idx, str) else sheet_names[name_or_idx]
            )
            
            logger.info(
                "[Excel 필드 추출] 시작: file=%s, sheet=%s, rows=%d, cols=%d",
                Path(excel_path).name,
                actual_sheet_name,
                len(df),
                len(df.columns),
            )
            
            # 2. 각 필드 추출
            fields_result = {}
            
            for field_name, definition in field_definitions.items():
                keywords = definition.get("keywords", [])
                post_process = definition.get("post_process")
                
                if not keywords:
                    continue
                
                # 키워드 매칭 (문자열 → 임베딩 순)
                match_info = self._find_field_value(df, field_name, keywords)
                
                if match_info:
                    value = match_info["value"]
                    
                    # 후처리 적용
                    if post_process and callable(post_process):
                        try:
                            value = post_process(value)
                        except Exception as e:
                            logger.warning(
                                "[Excel 필드 추출] 후처리 실패: field=%s, error=%s",
                                field_name,
                                e,
                            )
                    
                    fields_result[field_name] = {
                        "value": value,
                        "matched_keyword": match_info["keyword"],
                        "confidence": match_info["confidence"],
                        "location": match_info["location"],
                    }
                    
                    logger.info(
                        "[Excel 필드 추출] 성공: field=%s, value=%s, keyword=%s, location=(%d,%d)",
                        field_name,
                        value[:50] if len(value) > 50 else value,
                        match_info["keyword"],
                        match_info["location"]["row"],
                        match_info["location"]["col"],
                    )
                else:
                    logger.info(
                        "[Excel 필드 추출] 실패: field=%s, keywords=%s",
                        field_name,
                        keywords,
                    )
            
            return {
                "fields": fields_result,
                "metadata": {
                    "sheet_name": actual_sheet_name,
                    "row_count": len(df),
                    "col_count": len(df.columns),
                },
                "error": None,
            }
        
        except Exception as e:
            logger.exception("[Excel 필드 추출] 오류: %s", e)
            return {
                "fields": {},
                "metadata": {},
                "error": str(e),
            }
    
    def _find_field_value(
        self,
        df: pd.DataFrame,
        field_name: str,
        keywords: List[str],
    ) -> Optional[Dict[str, Any]]:
        """DataFrame에서 키워드를 찾고 주변 값을 추출합니다.
        
        Returns:
            {
                "value": str,
                "keyword": str,  # 실제 매칭된 키워드
                "confidence": float,
                "location": {"row": int, "col": int},
            }
        """
        # 1차: 문자열 기반 키워드 찾기
        match = self._find_keyword_string_based(df, keywords)
        
        if match:
            logger.info(
                "[Excel 필드 추출] 문자열 매칭 성공: field=%s, keyword=%s",
                field_name,
                match["keyword"],
            )
            return match
        
        # 2차: 임베딩 기반 의미 매칭
        if self.use_semantic_matching:
            logger.info(
                "[Excel 필드 추출] 문자열 매칭 실패 → 임베딩 기반 매칭 시도: field=%s",
                field_name,
            )
            match = self._find_keyword_semantic_based(df, field_name, keywords)
            
            if match:
                logger.info(
                    "[Excel 필드 추출] 임베딩 매칭 성공: field=%s, keyword=%s, score=%.3f",
                    field_name,
                    match["keyword"],
                    match["confidence"],
                )
                return match
        
        return None
    
    def _find_keyword_string_based(
        self,
        df: pd.DataFrame,
        keywords: List[str],
    ) -> Optional[Dict[str, Any]]:
        """문자열 기반으로 키워드를 찾고 주변 값을 추출합니다."""
        df_str = df.fillna("").astype(str)
        
        for keyword in keywords:
            normalized_keyword = self._normalize_text(keyword)
            
            # DataFrame 전체 순회
            for row_idx in range(len(df_str)):
                for col_idx in range(len(df_str.columns)):
                    cell_value = str(df_str.iloc[row_idx, col_idx])
                    normalized_cell = self._normalize_text(cell_value)
                    
                    # 키워드 매칭 (부분 포함도 허용)
                    if normalized_keyword in normalized_cell or normalized_cell in normalized_keyword:
                        # 값 찾기: 오른쪽 → 아래 → 왼쪽 순서
                        value = self._extract_value_near_keyword(
                            df_str, row_idx, col_idx
                        )
                        
                        if value and value.strip():
                            return {
                                "value": value.strip(),
                                "keyword": keyword,
                                "confidence": 0.95,  # 문자열 매칭은 높은 신뢰도
                                "location": {"row": row_idx, "col": col_idx},
                            }
        
        return None
    
    def _find_keyword_semantic_based(
        self,
        df: pd.DataFrame,
        field_name: str,
        keywords: List[str],
    ) -> Optional[Dict[str, Any]]:
        """임베딩 기반으로 의미가 유사한 셀을 찾고 값을 추출합니다."""
        try:
            if self._semantic_matcher is None:
                self._semantic_matcher = get_default_semantic_matcher()
        except Exception as e:
            logger.warning(
                "[Excel 필드 추출] 임베딩 매처 초기화 실패: %s",
                e,
            )
            return None
        
        df_str = df.fillna("").astype(str)
        
        # DataFrame의 모든 셀 텍스트 수집 (짧은 것만, 라벨로 보이는 것)
        candidates = []
        for row_idx in range(len(df_str)):
            for col_idx in range(len(df_str.columns)):
                cell_value = str(df_str.iloc[row_idx, col_idx]).strip()
                
                # 빈 값, 너무 긴 값, 숫자만 있는 값 제외
                if not cell_value or len(cell_value) > 20:
                    continue
                if re.fullmatch(r"[\d\W_]+", cell_value):
                    continue
                
                candidates.append({
                    "text": cell_value,
                    "row": row_idx,
                    "col": col_idx,
                })
        
        if not candidates:
            return None
        
        # 타겟: 필드명과 키워드들을 결합
        target = f"{field_name} / " + " / ".join(keywords)
        candidate_texts = [c["text"] for c in candidates]
        
        # 임베딩 기반 랭킹
        ranked = self._semantic_matcher.rank_candidates(
            target, candidate_texts, top_k=3
        )
        
        # 임계값 이상인 것만 사용
        for matched_text, score in ranked:
            if score < self.semantic_threshold:
                continue
            
            # 매칭된 셀 찾기
            for cand in candidates:
                if cand["text"] == matched_text:
                    # 값 추출
                    value = self._extract_value_near_keyword(
                        df_str, cand["row"], cand["col"]
                    )
                    
                    if value and value.strip():
                        return {
                            "value": value.strip(),
                            "keyword": matched_text,  # 실제 셀에 있던 텍스트
                            "confidence": float(score),
                            "location": {"row": cand["row"], "col": cand["col"]},
                        }
        
        return None
    
    def _extract_value_near_keyword(
        self,
        df_str: pd.DataFrame,
        row_idx: int,
        col_idx: int,
    ) -> str:
        """키워드 셀 주변에서 값을 추출합니다.
        
        우선순위:
        1. 오른쪽 셀
        2. 아래쪽 셀
        3. 왼쪽 셀
        """
        # 1. 오른쪽 (같은 행, 다음 열)
        if col_idx + 1 < len(df_str.columns):
            value = str(df_str.iloc[row_idx, col_idx + 1]).strip()
            if value and not self._is_label_like(value):
                return value
        
        # 2. 아래 (다음 행, 같은 열)
        if row_idx + 1 < len(df_str):
            value = str(df_str.iloc[row_idx + 1, col_idx]).strip()
            if value and not self._is_label_like(value):
                return value
        
        # 3. 왼쪽 (같은 행, 이전 열)
        if col_idx > 0:
            value = str(df_str.iloc[row_idx, col_idx - 1]).strip()
            if value and not self._is_label_like(value):
                return value
        
        return ""
    
    @staticmethod
    def _normalize_text(text: str) -> str:
        """텍스트 정규화 (띄어쓰기 제거, 소문자)."""
        text = re.sub(r"\s+", "", text)
        text = text.lower()
        return text
    
    @staticmethod
    def _is_label_like(text: str) -> bool:
        """텍스트가 라벨처럼 보이는지 판단 (콜론, 괄호 등)."""
        return bool(re.search(r"[:：\(\[\{]$", text.strip()))


# ===========================
# 헬퍼 함수
# ===========================

def extract_fields_from_excel(
    excel_path: Union[str, Path],
    field_definitions: Dict[str, Dict[str, Any]],
    sheet_name: Optional[Union[str, int]] = None,
    use_semantic_matching: bool = True,
) -> Dict[str, Any]:
    """Excel 파일에서 필드를 추출하는 헬퍼 함수.
    
    Args:
        excel_path: Excel 파일 경로
        field_definitions: 필드 정의
        sheet_name: 시트 이름/인덱스
        use_semantic_matching: 임베딩 사용 여부
    
    Returns:
        추출 결과
    
    Example:
        >>> field_defs = {
        ...     "company": {
        ...         "keywords": ["회사명", "업체명", "발행회사명"],
        ...         "post_process": lambda x: x.strip(),
        ...     },
        ...     "contact": {
        ...         "keywords": ["담당자명", "성명", "담당자"],
        ...     },
        ... }
        >>> result = extract_fields_from_excel("data.xlsx", field_defs)
        >>> print(result["fields"]["company"]["value"])
    """
    extractor = ExcelFieldExtractor(use_semantic_matching=use_semantic_matching)
    return extractor.extract_fields(excel_path, field_definitions, sheet_name)


def extract_simple_dict_from_excel(
    excel_path: Union[str, Path],
    keywords: Dict[str, List[str]],
    sheet_name: Optional[Union[str, int]] = None,
) -> Dict[str, str]:
    """Excel에서 간단한 필드 추출 (필드명 → 값만).
    
    Args:
        excel_path: Excel 파일 경로
        keywords: {"field_name": ["keyword1", "keyword2"], ...}
        sheet_name: 시트 이름/인덱스
    
    Returns:
        {"field_name": "value", ...}
    """
    field_defs = {
        field_name: {"keywords": kw_list}
        for field_name, kw_list in keywords.items()
    }
    
    result = extract_fields_from_excel(excel_path, field_defs, sheet_name)
    
    if result.get("error"):
        logger.error("[간단 추출] 오류: %s", result["error"])
        return {}
    
    return {
        field_name: data["value"]
        for field_name, data in result.get("fields", {}).items()
    }


# ===========================
# 표준 필드 정의
# ===========================

def get_standard_excel_field_definitions() -> Dict[str, Dict[str, Any]]:
    """표준 Excel 필드 정의 (한국 양식 기준)."""
    return {
        "회사명": {
            "keywords": ["회사명", "업체명", "발행회사명", "법인명"],
            "post_process": lambda x: x.strip(),
        },
        "담당자명": {
            "keywords": ["담당자명", "담당자", "성명", "이름"],
            "post_process": lambda x: x.strip(),
        },
        "사업자번호": {
            "keywords": ["사업자번호", "사업자 번호", "사업자등록번호"],
            "post_process": lambda x: x.replace(" ", "").replace("-", ""),
        },
        "담당자연락처": {
            "keywords": ["연락처", "담당자 연락처", "전화번호", "담당자 전화번호"],
            "post_process": lambda x: x.replace(" ", ""),
        },
        "회사주소": {
            "keywords": ["주소", "회사 주소", "소재지", "사업장 주소"],
            "post_process": lambda x: x.strip(),
        },
        "담당자이메일": {
            "keywords": ["이메일", "담당자 이메일", "Email"],
            "post_process": lambda x: x.strip().lower(),
        },
        "통화단위": {
            "keywords": ["통화", "통화 단위", "기본값", "통화단위"],
            "post_process": lambda x: x.strip().upper(),
        },
        "데이터기준기간시작일": {
            "keywords": ["데이터 기준기간 시작일", "데이터기준기간 시작일", "시작일", "기준기간 시작"],
            "post_process": lambda x: x.replace(" ", ""),
        },
        "데이터기준기간종료일": {
            "keywords": ["데이터 기준기간 종료일", "데이터기준기간 종료일", "종료일", "기준기간 종료"],
            "post_process": lambda x: x.replace(" ", ""),
        },
        # 생산량 섹션
        "연도": {
            "keywords": ["연도", "년도"],
            "post_process": lambda x: x.strip(),
        },
        "월": {
            "keywords": ["월"],
            "post_process": lambda x: x.strip(),
        },
        "사업장명": {
            "keywords": ["사업장명", "사업장", "사업장 이름"],
            "post_process": lambda x: x.strip(),
        },
        "제품명": {
            "keywords": ["제품명", "제품", "품목"],
            "post_process": lambda x: x.strip(),
        },
        "제품코드": {
            "keywords": ["제품코드", "제품 코드", "품목코드"],
            "post_process": lambda x: x.strip(),
        },
        "생산량": {
            "keywords": ["생산량", "수량"],
            "post_process": lambda x: x.replace(" ", "").replace(",", ""),
        },
        "단위": {
            "keywords": ["단위", "단위 (개, kg 등)", "단위(개, kg 등)"],
            "post_process": lambda x: x.strip(),
        },
    }
