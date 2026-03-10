"""Production-level Key-Value Extractor for PDF Forms.

PyMuPDF의 좌표 기반 텍스트 추출을 사용하여 다양한 표 레이아웃에서
Key-Value 쌍을 안정적으로 추출합니다.

지원 레이아웃:
- 수평 레이아웃: "성명" | "홍길동"
- 수평 역방향: "홍길동" | "성명"
- 수직 레이아웃: "성명" 위에 "홍길동"
- 혼합 레이아웃: 페이지마다 다른 구조

핵심 알고리즘:
1. bbox 기반 거리 계산 (유클리드 + 맨해튼 하이브리드)
2. 방향성 가중치 (same-line > right > below > left > above)
3. False positive 제거 (거리 임계값, 후보 검증)
"""

from __future__ import annotations

import re
import math
from typing import List, Dict, Any, Optional, Tuple, Set
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from app.domain.shared.bases.semantic_matcher import get_default_semantic_matcher
import logging

logger = logging.getLogger(__name__)

try:
    import fitz  # PyMuPDF
except ImportError:
    raise ImportError("PyMuPDF가 설치되지 않았습니다: pip install PyMuPDF")


class Direction(Enum):
    """Value의 위치 방향."""
    SAME_LINE = "same_line"  # 같은 줄
    RIGHT = "right"  # 오른쪽
    BELOW = "below"  # 아래
    LEFT = "left"  # 왼쪽
    ABOVE = "above"  # 위
    OTHER = "other"  # 기타


@dataclass
class BBox:
    """Bounding box 좌표 및 유틸리티."""
    x0: float
    y0: float
    x1: float
    y1: float
    
    @property
    def width(self) -> float:
        return self.x1 - self.x0
    
    @property
    def height(self) -> float:
        return self.y1 - self.y0
    
    @property
    def center_x(self) -> float:
        return (self.x0 + self.x1) / 2
    
    @property
    def center_y(self) -> float:
        return (self.y0 + self.y1) / 2
    
    @property
    def area(self) -> float:
        return self.width * self.height
    
    def distance_to(self, other: BBox) -> float:
        """다른 bbox까지의 유클리드 거리 (중심점 기준)."""
        dx = self.center_x - other.center_x
        dy = self.center_y - other.center_y
        return math.sqrt(dx * dx + dy * dy)
    
    def horizontal_distance(self, other: BBox) -> float:
        """수평 거리 (x축 차이)."""
        return abs(self.center_x - other.center_x)
    
    def vertical_distance(self, other: BBox) -> float:
        """수직 거리 (y축 차이)."""
        return abs(self.center_y - other.center_y)
    
    def is_same_line(self, other: BBox, tolerance: float = 5.0) -> bool:
        """같은 줄에 있는지 확인 (y 좌표 허용 오차)."""
        return self.vertical_distance(other) <= tolerance
    
    def is_aligned_horizontally(self, other: BBox, tolerance: float = 10.0) -> bool:
        """수평 정렬 여부 (같은 y 좌표 범위)."""
        # y 범위가 겹치는지 확인
        overlap_y = not (self.y1 < other.y0 or other.y1 < self.y0)
        close_enough = self.vertical_distance(other) <= tolerance
        return overlap_y or close_enough
    
    def is_aligned_vertically(self, other: BBox, tolerance: float = 10.0) -> bool:
        """수직 정렬 여부 (같은 x 좌표 범위)."""
        overlap_x = not (self.x1 < other.x0 or other.x1 < self.x0)
        close_enough = self.horizontal_distance(other) <= tolerance
        return overlap_x or close_enough
    
    def overlaps(self, other: BBox) -> bool:
        """두 bbox가 겹치는지 확인."""
        return not (self.x1 < other.x0 or other.x1 < self.x0 or
                    self.y1 < other.y0 or other.y1 < self.y0)


@dataclass
class Word:
    """단어 정보 (PyMuPDF의 word 데이터)."""
    text: str
    bbox: BBox
    block_no: int
    line_no: int
    word_no: int
    
    def __repr__(self) -> str:
        return f"Word('{self.text}', bbox=({self.bbox.x0:.1f}, {self.bbox.y0:.1f}, {self.bbox.x1:.1f}, {self.bbox.y1:.1f}))"


@dataclass
class KeyValuePair:
    """추출된 Key-Value 쌍."""
    key: str
    value: str
    key_bbox: BBox
    value_bbox: BBox
    direction: Direction
    distance: float
    confidence: float
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환."""
        return {
            "key": self.key,
            "value": self.value,
            "key_bbox": [self.key_bbox.x0, self.key_bbox.y0, self.key_bbox.x1, self.key_bbox.y1],
            "value_bbox": [self.value_bbox.x0, self.value_bbox.y0, self.value_bbox.x1, self.value_bbox.y1],
            "direction": self.direction.value,
            "distance": round(self.distance, 2),
            "confidence": round(self.confidence, 3),
        }


class KeyValueExtractor:
    """다양한 표 레이아웃에서 Key-Value를 추출하는 production-level extractor.
    
    특징:
    - 방향별 가중치 적용 (same_line > right > below > left > above)
    - 거리 기반 후보 필터링
    - False positive 제거 (키워드 중복, 너무 먼 거리)
    - 다양한 키워드 변형 지원 (띄어쓰기, 동의어)
    """
    
    def __init__(
        self,
        max_distance: float = 300.0,
        same_line_tolerance: float = 5.0,
        direction_weights: Optional[Dict[Direction, float]] = None,
    ):
        """
        Args:
            max_distance: 최대 허용 거리 (픽셀). 이보다 먼 value는 제외
            same_line_tolerance: 같은 줄로 판단하는 y축 허용 오차
            direction_weights: 방향별 가중치 (기본값: 아래 참조)
        """
        self.max_distance = max_distance
        self.same_line_tolerance = same_line_tolerance
        
        # 기본 방향별 가중치 (높을수록 선호)
        if direction_weights is None:
            direction_weights = {
                Direction.SAME_LINE: 10.0,  # 같은 줄 최우선
                Direction.RIGHT: 5.0,       # 오른쪽
                Direction.BELOW: 4.0,       # 아래
                Direction.LEFT: 2.0,        # 왼쪽 (덜 일반적)
                Direction.ABOVE: 1.0,       # 위 (매우 드뭄)
                Direction.OTHER: 0.1,       # 기타 (거의 사용 안 함)
            }
        self.direction_weights = direction_weights
        # 의미 기반 키워드 매칭 (임베딩) 지원 여부는 지연 초기화
        self._semantic_matcher = None
    
    def extract_from_pdf(
        self,
        pdf_path: str | Path,
        page_num: int,
        keywords: Dict[str, List[str]],
    ) -> Dict[str, KeyValuePair]:
        """PDF 페이지에서 Key-Value 추출.
        
        Args:
            pdf_path: PDF 파일 경로
            page_num: 페이지 번호 (1-based)
            keywords: 추출할 필드와 키워드 매핑
                예: {"name": ["성명", "이름", "Name"], "birth": ["생년월일", "출생일"]}
        
        Returns:
            필드명 → KeyValuePair 매핑
        
        Example:
            >>> extractor = KeyValueExtractor()
            >>> keywords = {
            ...     "name": ["성명", "이름"],
            ...     "company": ["업체명", "회사명"],
            ... }
            >>> result = extractor.extract_from_pdf("form.pdf", 1, keywords)
            >>> print(result["name"].value)  # "홍길동"
        """
        # 1. PyMuPDF로 단어 추출
        words = self._extract_words_from_pdf(pdf_path, page_num)
        
        # 2. 각 필드별로 Key-Value 매칭
        result = {}
        for field_name, keyword_list in keywords.items():
            kv_pair = self._find_best_match(words, keyword_list)
            if kv_pair:
                result[field_name] = kv_pair
        
        return result
    
    def extract_from_words(
        self,
        words: List[Word],
        keywords: Dict[str, List[str]],
    ) -> Dict[str, KeyValuePair]:
        """이미 추출된 Word 리스트에서 Key-Value 추출.
        
        Args:
            words: Word 객체 리스트
            keywords: 추출할 필드와 키워드 매핑
        
        Returns:
            필드명 → KeyValuePair 매핑
        """
        result = {}
        for field_name, keyword_list in keywords.items():
            kv_pair = self._find_best_match(words, keyword_list)
            if kv_pair:
                result[field_name] = kv_pair
        
        return result
    
    def _extract_words_from_pdf(
        self,
        pdf_path: str | Path,
        page_num: int,
    ) -> List[Word]:
        """PyMuPDF로 단어 추출 (bbox 포함).
        
        Returns:
            Word 객체 리스트
        """
        doc = fitz.open(str(pdf_path))
        try:
            if page_num < 1 or page_num > len(doc):
                raise ValueError(f"페이지 번호 {page_num}이 범위를 벗어났습니다.")
            
            page = doc[page_num - 1]
            # get_text("words") 형식: (x0, y0, x1, y1, "word", block_no, line_no, word_no)
            raw_words = page.get_text("words")
            
            words = []
            for item in raw_words:
                x0, y0, x1, y1, text, block_no, line_no, word_no = item
                
                # 빈 텍스트 제외
                if not text.strip():
                    continue
                
                word = Word(
                    text=text.strip(),
                    bbox=BBox(x0, y0, x1, y1),
                    block_no=block_no,
                    line_no=line_no,
                    word_no=word_no,
                )
                words.append(word)
            
            return words
        finally:
            doc.close()
    
    def _find_best_match(
        self,
        words: List[Word],
        keywords: List[str],
    ) -> Optional[KeyValuePair]:
        """주어진 키워드 리스트 중 하나를 찾아 가장 적합한 Value를 매칭.
        
        Args:
            words: 전체 단어 리스트
            keywords: 찾을 키워드 리스트 (동의어 포함)
        
        Returns:
            최적의 KeyValuePair 또는 None
        """
        # 1. 키워드 찾기 (문자열 기반 1차 매칭)
        key_words = self._find_keywords(words, keywords)
        
        # 1-2. 1차 매칭 실패 시 임베딩 기반 의미 매칭으로 폴백
        if not key_words:
            matcher = self._get_semantic_matcher()
            if matcher is not None:
                logger.info(
                    "[KeyValueExtractor] 문자열 키워드 매칭 실패 → 임베딩 기반 매칭 시도 "
                    "(keywords=%s, words=%d)",
                    repr(keywords),
                    len(words),
                )
                key_words = self._find_keywords_semantic(words, keywords)
                logger.info(
                    "[KeyValueExtractor] 임베딩 기반 매칭 결과: matched_keys=%d",
                    len(key_words),
                )
            if not key_words:
                logger.info(
                    "[KeyValueExtractor] 키워드 매칭 실패 (문자열 + 임베딩 모두 실패, keywords=%s)",
                    repr(keywords),
                )
                return None
        
        # 2. 각 키워드에 대해 가장 가까운 value 찾기
        best_pair = None
        best_score = -1.0
        
        for key_word in key_words:
            candidates = self._find_value_candidates(key_word, words)
            
            if not candidates:
                continue
            
            # 3. 후보 중 최고 점수 선택
            for candidate in candidates:
                score = self._calculate_score(
                    key_word.bbox,
                    candidate["word"].bbox,
                    candidate["direction"],
                    candidate["distance"],
                )
                
                # 더 높은 점수의 쌍 발견
                if score > best_score:
                    best_score = score
                    best_pair = KeyValuePair(
                        key=key_word.text,
                        value=candidate["word"].text,
                        key_bbox=key_word.bbox,
                        value_bbox=candidate["word"].bbox,
                        direction=candidate["direction"],
                        distance=candidate["distance"],
                        confidence=self._calculate_confidence(score, candidate["direction"]),
                    )
        
        return best_pair
    
    def _find_keywords(
        self,
        words: List[Word],
        keywords: List[str],
    ) -> List[Word]:
        """키워드에 해당하는 Word 찾기.
        
        띄어쓰기 무시, 대소문자 무시하여 매칭.
        """
        found = []
        
        for word in words:
            normalized_word = self._normalize_text(word.text)
            
            for keyword in keywords:
                normalized_keyword = self._normalize_text(keyword)
                
                # 정확히 일치하는 경우
                if normalized_word == normalized_keyword:
                    found.append(word)
                    break
                
                # 부분 일치 (키워드가 단어에 포함)
                # 예: "성명" in "담당자성명"
                if normalized_keyword in normalized_word and len(normalized_keyword) >= 2:
                    found.append(word)
                    break
        
        return found
    
    def _get_semantic_matcher(self):
        """지연 초기화된 SemanticFieldMatcher 인스턴스를 반환."""
        if self._semantic_matcher is not None:
            return self._semantic_matcher
        try:
            self._semantic_matcher = get_default_semantic_matcher()
        except Exception:
            self._semantic_matcher = None
        return self._semantic_matcher

    def _find_keywords_semantic(
        self,
        words: List[Word],
        keywords: List[str],
        threshold: float = 0.8,
    ) -> List[Word]:
        """임베딩 기반으로 키워드에 해당할 가능성이 높은 라벨 Word 찾기.

        문자열 기반 매칭에 실패했을 때만 호출되며,
        - 짧은 텍스트(라벨일 가능성이 높은 단어)만 후보로 사용
        - top-k 후보 중 임계값 이상인 것만 key로 간주
        """
        matcher = self._get_semantic_matcher()
        if matcher is None or not keywords or not words:
            return []

        # 타깃 표현: 키워드들을 하나의 질의 문장처럼 결합
        # 예: ["성명", "담당자명"] → "성명 / 담당자명"
        target = " / ".join(sorted(set(k for k in keywords if k.strip())))
        if not target:
            return []

        candidate_labels = []
        label_to_word: Dict[str, Word] = {}

        for idx, w in enumerate(words):
            raw = w.text.strip()
            if not raw:
                continue
            # 너무 긴 텍스트나 숫자/기호 위주의 텍스트는 라벨로 보기 어렵기 때문에 제외
            if len(raw) > 12:
                continue
            if re.fullmatch(r"[\d\W_]+", raw):
                continue

            label = f"{raw}@@{idx}"
            candidate_labels.append(label)
            label_to_word[label] = w

        if not candidate_labels:
            return []

        ranked = matcher.rank_candidates(target, candidate_labels, top_k=5)
        result: List[Word] = []
        seen_ids: Set[int] = set()

        for label, score in ranked:
            if score < threshold:
                continue
            w = label_to_word.get(label)
            if w is None:
                continue
            wid = id(w)
            if wid in seen_ids:
                continue
            seen_ids.add(wid)
            result.append(w)

        return result
    
    def _find_value_candidates(
        self,
        key_word: Word,
        all_words: List[Word],
    ) -> List[Dict[str, Any]]:
        """키워드 주변의 value 후보 찾기.
        
        Returns:
            [{"word": Word, "direction": Direction, "distance": float}, ...]
        """
        candidates = []
        key_text_normalized = self._normalize_text(key_word.text)
        
        for word in all_words:
            # 자기 자신 제외
            if word is key_word:
                continue
            
            # 같은 키워드 텍스트 제외 (중복 방지)
            word_text_normalized = self._normalize_text(word.text)
            if word_text_normalized == key_text_normalized:
                continue
            
            # 거리 계산
            distance = key_word.bbox.distance_to(word.bbox)
            
            # 최대 거리 초과 제외
            if distance > self.max_distance:
                continue
            
            # 방향 판단
            direction = self._determine_direction(key_word.bbox, word.bbox)
            
            # 너무 작은 텍스트 제외 (아이콘, 기호 등)
            if len(word.text.strip()) < 1:
                continue
            
            # 명백한 라벨 텍스트 제외 (콜론, 괄호로 끝나는 경우)
            if re.search(r'[:：\(\[\{]$', word.text.strip()):
                continue
            
            candidates.append({
                "word": word,
                "direction": direction,
                "distance": distance,
            })
        
        return candidates
    
    def _determine_direction(self, key_bbox: BBox, value_bbox: BBox) -> Direction:
        """Key에서 Value의 방향 판단.
        
        우선순위:
        1. SAME_LINE: 같은 줄에 있는 경우
        2. RIGHT/LEFT/BELOW/ABOVE: 주된 방향
        """
        # 같은 줄 체크
        if key_bbox.is_same_line(value_bbox, self.same_line_tolerance):
            if value_bbox.center_x > key_bbox.center_x:
                return Direction.SAME_LINE  # 실제로는 오른쪽이지만 same_line으로 표시
            else:
                return Direction.LEFT
        
        # 수평/수직 거리 비교
        h_dist = key_bbox.horizontal_distance(value_bbox)
        v_dist = key_bbox.vertical_distance(value_bbox)
        
        # 수평 방향이 더 지배적
        if h_dist > v_dist:
            if value_bbox.center_x > key_bbox.center_x:
                return Direction.RIGHT
            else:
                return Direction.LEFT
        # 수직 방향이 더 지배적
        else:
            if value_bbox.center_y > key_bbox.center_y:
                return Direction.BELOW
            else:
                return Direction.ABOVE
    
    def _calculate_score(
        self,
        key_bbox: BBox,
        value_bbox: BBox,
        direction: Direction,
        distance: float,
    ) -> float:
        """Key-Value 쌍의 적합성 점수 계산.
        
        점수 = (방향 가중치) / (거리 + 1)
        
        높은 점수 = 더 적합한 매칭
        """
        direction_weight = self.direction_weights.get(direction, 0.1)
        
        # 거리 페널티 (가까울수록 높은 점수)
        distance_penalty = distance + 1.0
        
        # 정렬 보너스
        alignment_bonus = 1.0
        if direction in [Direction.SAME_LINE, Direction.RIGHT, Direction.LEFT]:
            # 수평 정렬이 잘 되어 있으면 보너스
            if key_bbox.is_aligned_horizontally(value_bbox, tolerance=15.0):
                alignment_bonus = 1.5
        elif direction in [Direction.BELOW, Direction.ABOVE]:
            # 수직 정렬이 잘 되어 있으면 보너스
            if key_bbox.is_aligned_vertically(value_bbox, tolerance=15.0):
                alignment_bonus = 1.5
        
        score = (direction_weight * alignment_bonus) / distance_penalty
        return score
    
    def _calculate_confidence(self, score: float, direction: Direction) -> float:
        """점수를 0~1 신뢰도로 변환.
        
        휴리스틱 기반 변환:
        - SAME_LINE + 높은 점수 = 높은 신뢰도
        - OTHER + 낮은 점수 = 낮은 신뢰도
        """
        # 로그 스케일링으로 0~1 범위로 변환
        confidence = 1.0 / (1.0 + math.exp(-score + 1.0))
        
        # 방향에 따른 보정
        if direction == Direction.SAME_LINE:
            confidence = min(1.0, confidence * 1.2)
        elif direction == Direction.OTHER:
            confidence = confidence * 0.5
        
        return max(0.0, min(1.0, confidence))
    
    @staticmethod
    def _normalize_text(text: str) -> str:
        """텍스트 정규화 (띄어쓰기 제거, 소문자 변환)."""
        text = re.sub(r'\s+', '', text)  # 모든 공백 제거
        text = text.lower()
        return text


class MultiKeywordExtractor(KeyValueExtractor):
    """여러 필드를 한 번에 추출하는 확장 클래스.
    
    추가 기능:
    - 한 페이지에서 여러 필드 동시 추출
    - 중복 value 방지 (이미 매칭된 word는 재사용 안 함)
    - 필드별 커스텀 후처리 지원
    """
    
    def extract_fields(
        self,
        pdf_path: str | Path,
        page_num: int,
        field_definitions: Dict[str, Dict[str, Any]],
    ) -> Dict[str, Any]:
        """여러 필드를 한 번에 추출.
        
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
        
        Returns:
            {
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
                "raw_words": List[dict],  # 디버깅용
            }
        
        Example:
            >>> extractor = MultiKeywordExtractor()
            >>> field_defs = {
            ...     "name": {
            ...         "keywords": ["성명", "이름", "Name"],
            ...         "post_process": lambda x: x.strip(),
            ...     },
            ...     "birth_date": {
            ...         "keywords": ["생년월일", "출생일"],
            ...         "post_process": lambda x: x.replace(" ", ""),
            ...     },
            ... }
            >>> result = extractor.extract_fields("form.pdf", 1, field_defs)
        """
        # 1. 단어 추출
        words = self._extract_words_from_pdf(pdf_path, page_num)
        
        # 2. 이미 사용된 value word 추적 (중복 방지)
        used_value_words: Set[int] = set()  # word 객체의 id로 추적
        
        # 3. 각 필드별 추출
        fields_result = {}
        
        for field_name, definition in field_definitions.items():
            keywords = definition.get("keywords", [])
            post_process = definition.get("post_process")
            
            if not keywords:
                continue
            
            # 사용되지 않은 단어만으로 매칭
            available_words = [w for w in words if id(w) not in used_value_words]
            
            kv_pair = self._find_best_match(available_words, keywords)
            
            if kv_pair:
                # 후처리 적용
                value = kv_pair.value
                if post_process and callable(post_process):
                    try:
                        value = post_process(value)
                    except Exception:
                        pass  # 후처리 실패 시 원본 유지
                
                # 결과 저장
                fields_result[field_name] = {
                    "value": value,
                    "key": kv_pair.key,
                    "confidence": kv_pair.confidence,
                    "direction": kv_pair.direction.value,
                    "distance": kv_pair.distance,
                    "bbox": {
                        "key": [kv_pair.key_bbox.x0, kv_pair.key_bbox.y0, 
                               kv_pair.key_bbox.x1, kv_pair.key_bbox.y1],
                        "value": [kv_pair.value_bbox.x0, kv_pair.value_bbox.y0,
                                 kv_pair.value_bbox.x1, kv_pair.value_bbox.y1],
                    }
                }
                
                # 매칭된 value word를 사용됨으로 표시
                # (key는 다른 필드에서 재사용 가능)
                for w in words:
                    if (w.bbox.x0 == kv_pair.value_bbox.x0 and 
                        w.bbox.y0 == kv_pair.value_bbox.y0 and
                        w.text == kv_pair.value):
                        used_value_words.add(id(w))
                        break
        
        # 4. 디버깅용 raw words 포함
        raw_words_data = [
            {
                "text": w.text,
                "bbox": [w.bbox.x0, w.bbox.y0, w.bbox.x1, w.bbox.y1],
                "block": w.block_no,
                "line": w.line_no,
            }
            for w in words
        ]
        
        return {
            "fields": fields_result,
            "raw_words": raw_words_data,
        }


class OCRKeyValueExtractor:
    """EasyOCR 결과에서 Key-Value 추출 (스캔 PDF용).
    
    EasyOCR의 bbox 형식: [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
    PyMuPDF와 달리 4개 점으로 표현 (회전/기울어진 텍스트 지원)
    """
    
    def __init__(
        self,
        max_distance: float = 300.0,
        same_line_tolerance: float = 10.0,
    ):
        self.max_distance = max_distance
        self.same_line_tolerance = same_line_tolerance
        self.base_extractor = KeyValueExtractor(max_distance, same_line_tolerance)
    
    def extract_from_ocr_results(
        self,
        ocr_results: List[Tuple[List, str, float]],
        keywords: Dict[str, List[str]],
        min_confidence: float = 0.5,
    ) -> Dict[str, KeyValuePair]:
        """EasyOCR 결과에서 Key-Value 추출.
        
        Args:
            ocr_results: EasyOCR 결과 [(bbox, text, confidence), ...]
            keywords: 필드명 → 키워드 리스트 매핑
            min_confidence: 최소 신뢰도
        
        Returns:
            필드명 → KeyValuePair 매핑
        """
        # 1. OCR 결과를 Word 형식으로 변환
        words = []
        for idx, (bbox, text, confidence) in enumerate(ocr_results):
            if confidence < min_confidence:
                continue
            
            # EasyOCR bbox: [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
            # → BBox (x0, y0, x1, y1)로 변환
            x_coords = [point[0] for point in bbox]
            y_coords = [point[1] for point in bbox]
            
            x0, x1 = min(x_coords), max(x_coords)
            y0, y1 = min(y_coords), max(y_coords)
            
            word = Word(
                text=text.strip(),
                bbox=BBox(x0, y0, x1, y1),
                block_no=0,
                line_no=idx,
                word_no=idx,
            )
            words.append(word)
        
        # 2. 기본 extractor로 매칭
        return self.base_extractor.extract_from_words(words, keywords)
    
    def extract_fields_from_ocr(
        self,
        ocr_results: List[Tuple[List, str, float]],
        field_definitions: Dict[str, Dict[str, Any]],
        min_confidence: float = 0.5,
    ) -> Dict[str, Any]:
        """EasyOCR 결과에서 여러 필드 동시 추출.
        
        Args:
            ocr_results: EasyOCR 결과
            field_definitions: 필드 정의
            min_confidence: 최소 신뢰도
        
        Returns:
            추출된 필드 딕셔너리
        """
        # Word 변환
        words = []
        for idx, (bbox, text, confidence) in enumerate(ocr_results):
            if confidence < min_confidence:
                continue
            
            x_coords = [point[0] for point in bbox]
            y_coords = [point[1] for point in bbox]
            
            x0, x1 = min(x_coords), max(x_coords)
            y0, y1 = min(y_coords), max(y_coords)
            
            word = Word(
                text=text.strip(),
                bbox=BBox(x0, y0, x1, y1),
                block_no=0,
                line_no=idx,
                word_no=idx,
            )
            words.append(word)
        
        # MultiKeywordExtractor 사용
        extractor = MultiKeywordExtractor(self.max_distance, self.same_line_tolerance)
        
        # 임시로 extract_from_words 로직 재구성
        used_value_words: Set[int] = set()
        fields_result = {}
        
        for field_name, definition in field_definitions.items():
            keywords = definition.get("keywords", [])
            post_process = definition.get("post_process")
            
            if not keywords:
                continue
            
            available_words = [w for w in words if id(w) not in used_value_words]
            
            kv_pair = extractor._find_best_match(available_words, keywords)
            
            if kv_pair:
                value = kv_pair.value
                if post_process and callable(post_process):
                    try:
                        value = post_process(value)
                    except Exception:
                        pass
                
                fields_result[field_name] = {
                    "value": value,
                    "key": kv_pair.key,
                    "confidence": kv_pair.confidence,
                    "direction": kv_pair.direction.value,
                    "distance": kv_pair.distance,
                    "bbox": {
                        "key": [kv_pair.key_bbox.x0, kv_pair.key_bbox.y0, 
                               kv_pair.key_bbox.x1, kv_pair.key_bbox.y1],
                        "value": [kv_pair.value_bbox.x0, kv_pair.value_bbox.y0,
                                 kv_pair.value_bbox.x1, kv_pair.value_bbox.y1],
                    }
                }
                
                # 사용된 value word 표시
                for w in words:
                    if (w.bbox.x0 == kv_pair.value_bbox.x0 and 
                        w.bbox.y0 == kv_pair.value_bbox.y0 and
                        w.text == kv_pair.value):
                        used_value_words.add(id(w))
                        break
        
        return {
            "fields": fields_result,
            "raw_words": [{"text": w.text, "bbox": [w.bbox.x0, w.bbox.y0, w.bbox.x1, w.bbox.y1]} for w in words],
        }


# ===========================
# 헬퍼 함수
# ===========================

def extract_simple(
    pdf_path: str | Path,
    page_num: int,
    keywords: Dict[str, List[str]],
) -> Dict[str, str]:
    """간단한 추출 함수 (필드명 → 값 매핑만 반환).
    
    Args:
        pdf_path: PDF 파일 경로
        page_num: 페이지 번호 (1-based)
        keywords: {"field_name": ["keyword1", "keyword2"], ...}
    
    Returns:
        {"field_name": "value", ...}
    
    Example:
        >>> result = extract_simple("form.pdf", 1, {
        ...     "name": ["성명", "이름"],
        ...     "company": ["업체명", "회사명"],
        ... })
        >>> print(result["name"])  # "홍길동"
    """
    extractor = KeyValueExtractor()
    kv_pairs = extractor.extract_from_pdf(pdf_path, page_num, keywords)
    
    return {
        field_name: pair.value
        for field_name, pair in kv_pairs.items()
    }


def extract_with_details(
    pdf_path: str | Path,
    page_num: int,
    field_definitions: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    """상세 정보를 포함한 추출 (bbox, confidence 등).
    
    Args:
        pdf_path: PDF 파일 경로
        page_num: 페이지 번호 (1-based)
        field_definitions: 필드 정의
            {
                "field_name": {
                    "keywords": ["keyword1", "keyword2"],
                    "post_process": Optional[Callable]
                }
            }
    
    Returns:
        {
            "fields": {field_name: {value, key, confidence, direction, ...}},
            "raw_words": [...],
        }
    """
    extractor = MultiKeywordExtractor()
    return extractor.extract_fields(pdf_path, page_num, field_definitions)


def extract_from_ocr_simple(
    ocr_results: List[Tuple[List, str, float]],
    keywords: Dict[str, List[str]],
    min_confidence: float = 0.5,
) -> Dict[str, str]:
    """EasyOCR 결과에서 간단한 추출 (필드명 → 값만).
    
    Args:
        ocr_results: EasyOCR readtext() 결과
        keywords: 필드명 → 키워드 리스트
        min_confidence: 최소 OCR 신뢰도
    
    Returns:
        {"field_name": "value", ...}
    """
    extractor = OCRKeyValueExtractor()
    kv_pairs = extractor.extract_from_ocr_results(ocr_results, keywords, min_confidence)
    
    return {
        field_name: pair.value
        for field_name, pair in kv_pairs.items()
    }
