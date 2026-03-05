"""Word 문서 추출 인터페이스."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Dict, Any, Union


class WordExtractionStrategy(ABC):
    """Word 문서에서 텍스트/구조를 추출하는 전략 인터페이스."""

    @abstractmethod
    def extract_text(self, source: Union[str, Path]) -> str:
        """문서 전체 텍스트를 추출합니다."""
        pass

    @abstractmethod
    def extract_paragraphs(self, source: Union[str, Path]) -> List[str]:
        """단락(paragraph) 리스트를 추출합니다."""
        pass

    @abstractmethod
    def extract_tables(self, source: Union[str, Path]) -> List[Dict[str, Any]]:
        """표 데이터를 추출합니다. 각 표는 행 리스트 등으로 표현."""
        pass
