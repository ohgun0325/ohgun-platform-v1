"""Excel 문서 추출 인터페이스."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Dict, Any, Union, Optional


class ExcelExtractionStrategy(ABC):
    """Excel 문서에서 시트/테이블 데이터를 추출하는 전략 인터페이스."""

    @abstractmethod
    def get_sheet_names(self, source: Union[str, Path]) -> List[str]:
        """시트 이름 목록을 반환합니다."""
        pass

    @abstractmethod
    def read_sheet(
        self,
        source: Union[str, Path],
        sheet_name: Optional[Union[str, int]] = None,
    ) -> Dict[str, Any]:
        """시트 하나를 읽어 딕셔너리(또는 DataFrame 직렬화)로 반환합니다."""
        pass

    @abstractmethod
    def read_all_sheets(self, source: Union[str, Path]) -> Dict[str, Dict[str, Any]]:
        """모든 시트를 읽어 시트명을 키로 하는 딕셔너리로 반환합니다."""
        pass
