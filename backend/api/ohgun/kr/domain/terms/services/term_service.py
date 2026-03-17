"""ODA 용어사전 서비스

용어사전 데이터를 로드하고 검색하는 기능을 제공합니다.
"""

from pathlib import Path
from typing import Optional

from domain.terms.models.oda_term import (
    ODATermDictionary,
    ODATermEntry,
)


class TermService:
    """ODA 용어사전 서비스 클래스"""

    def __init__(self, jsonl_file_path: Optional[str] = None):
        """서비스 초기화

        Args:
            jsonl_file_path: JSONL 파일 경로. None이면 기본 경로 사용
        """
        if jsonl_file_path is None:
            # 기본 경로 설정
            base_path = Path(__file__).parent.parent.parent.parent.parent
            jsonl_file_path = str(
                base_path / "data" / "koica_data" / "한국국제협력단_ODA 용어사전_20230612.jsonl"
            )

        self.jsonl_file_path = jsonl_file_path
        self._dictionary: Optional[ODATermDictionary] = None

    @property
    def dictionary(self) -> ODATermDictionary:
        """용어사전 인스턴스 (lazy loading)"""
        if self._dictionary is None:
            self._dictionary = ODATermDictionary.from_jsonl_file(self.jsonl_file_path)
        return self._dictionary

    def reload(self) -> None:
        """용어사전 다시 로드"""
        self._dictionary = None
        _ = self.dictionary  # 강제 로드

    def search_terms(self, query: str, limit: int = 10, search_type: str = "all") -> list[ODATermEntry]:
        """용어 검색

        Args:
            query: 검색어
            limit: 최대 결과 수
            search_type: 검색 타입 ('title', 'content', 'all')

        Returns:
            검색된 용어 목록
        """
        results = self.dictionary.search_terms(query, search_type)
        return results[:limit]

    def get_term_by_korean_name(self, name: str) -> Optional[ODATermEntry]:
        """한글명으로 용어 조회"""
        return self.dictionary.get_term_by_korean_name(name)

    def get_term_by_english_name(self, name: str) -> Optional[ODATermEntry]:
        """영문명으로 용어 조회"""
        return self.dictionary.get_term_by_english_name(name)

    def get_term_by_abbreviation(self, abbr: str) -> Optional[ODATermEntry]:
        """약어로 용어 조회"""
        return self.dictionary.get_term_by_abbreviation(abbr)

    def get_all_terms(self, limit: Optional[int] = None) -> list[ODATermEntry]:
        """모든 용어 조회

        Args:
            limit: 최대 결과 수 (None이면 전체)

        Returns:
            용어 목록
        """
        terms = self.dictionary.terms
        if limit is not None:
            return terms[:limit]
        return terms

    def get_total_count(self) -> int:
        """전체 용어 수 반환"""
        return len(self.dictionary.terms)
