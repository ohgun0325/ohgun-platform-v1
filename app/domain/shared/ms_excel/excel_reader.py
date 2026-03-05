"""pandas 기반 Excel(.xlsx, .xls) 파일 읽기."""

from __future__ import annotations

from pathlib import Path
from typing import List, Dict, Any, Union, Optional

try:
    import pandas as pd
except ImportError:
    raise ImportError("pandas가 필요합니다. pip install pandas openpyxl")

from app.domain.shared.ms_excel.base import ExcelExtractionStrategy


class PandasExcelReader(ExcelExtractionStrategy):
    """pandas를 사용한 Excel 파일 읽기. .xlsx(openpyxl), .xls 엔진 지원."""

    def get_sheet_names(self, source: Union[str, Path]) -> List[str]:
        """시트 이름 목록을 반환합니다.

        Args:
            source: .xlsx 또는 .xls 파일 경로

        Returns:
            시트 이름 리스트
        """
        xl = pd.ExcelFile(str(source))
        return xl.sheet_names

    def read_sheet(
        self,
        source: Union[str, Path],
        sheet_name: Optional[Union[str, int]] = None,
    ) -> Dict[str, Any]:
        """시트 하나를 읽어 딕셔너리로 반환합니다.

        Args:
            source: Excel 파일 경로
            sheet_name: 시트 이름 또는 0-based 인덱스. None이면 첫 시트.

        Returns:
            {"sheet_name": str, "columns": [...], "data": [[...], ...], "row_count", "col_count"}
        """
        xl = pd.ExcelFile(str(source))
        name_or_idx = sheet_name if sheet_name is not None else 0
        df = pd.read_excel(xl, sheet_name=name_or_idx)
        actual_name = xl.sheet_names[name_or_idx] if isinstance(name_or_idx, int) else name_or_idx
        if df.empty:
            return {
                "sheet_name": actual_name,
                "columns": [],
                "data": [],
                "row_count": 0,
                "col_count": 0,
            }
        data = df.fillna("").astype(str).values.tolist()
        return {
            "sheet_name": actual_name,
            "columns": df.columns.astype(str).tolist(),
            "data": data,
            "row_count": len(data),
            "col_count": len(df.columns),
        }

    def read_all_sheets(self, source: Union[str, Path]) -> Dict[str, Dict[str, Any]]:
        """모든 시트를 읽어 시트명을 키로 하는 딕셔너리로 반환합니다.

        Args:
            source: Excel 파일 경로

        Returns:
            { "시트이름": read_sheet 결과, ... }
        """
        names = self.get_sheet_names(source)
        return {name: self.read_sheet(source, sheet_name=name) for name in names}

    def read_dataframe(
        self,
        source: Union[str, Path],
        sheet_name: Optional[Union[str, int]] = None,
    ) -> "pd.DataFrame":
        """시트를 pandas DataFrame으로 반환합니다. (고급 활용용)

        Args:
            source: Excel 파일 경로
            sheet_name: 시트 이름 또는 인덱스

        Returns:
            pandas DataFrame
        """
        return pd.read_excel(str(source), sheet_name=sheet_name or 0)


def read_excel_sheet(
    path: Union[str, Path],
    sheet_name: Optional[Union[str, int]] = None,
) -> Dict[str, Any]:
    """Excel 파일에서 시트 하나를 읽는 헬퍼 함수."""
    return PandasExcelReader().read_sheet(path, sheet_name=sheet_name)


def read_excel_all_sheets(path: Union[str, Path]) -> Dict[str, Dict[str, Any]]:
    """Excel 파일의 모든 시트를 읽는 헬퍼 함수."""
    return PandasExcelReader().read_all_sheets(path)


def get_excel_sheet_names(path: Union[str, Path]) -> List[str]:
    """Excel 파일의 시트 이름 목록을 반환하는 헬퍼 함수."""
    return PandasExcelReader().get_sheet_names(path)
