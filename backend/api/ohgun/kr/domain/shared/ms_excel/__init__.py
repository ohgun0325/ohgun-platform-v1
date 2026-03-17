"""Excel(.xlsx, .xls) 문서 처리 모듈.

pandas와 openpyxl을 사용하여 Excel 파일을 읽습니다.

사용 예시:
    from domain.shared.ms_excel import read_excel_sheet, read_excel_all_sheets
    data = read_excel_sheet("data.xlsx")
    all_data = read_excel_all_sheets("data.xlsx")
    
    # 필드 자동 추출
    from domain.shared.ms_excel import extract_fields_from_excel
    result = extract_fields_from_excel("data.xlsx", field_definitions)
"""

from domain.shared.ms_excel.base import ExcelExtractionStrategy
from domain.shared.ms_excel.excel_reader import (
    PandasExcelReader,
    read_excel_sheet,
    read_excel_all_sheets,
    get_excel_sheet_names,
)
from domain.shared.ms_excel.field_extractor import (
    ExcelFieldExtractor,
    extract_fields_from_excel,
    extract_simple_dict_from_excel,
    get_standard_excel_field_definitions,
)

__all__ = [
    "ExcelExtractionStrategy",
    "PandasExcelReader",
    "read_excel_sheet",
    "read_excel_all_sheets",
    "get_excel_sheet_names",
    "ExcelFieldExtractor",
    "extract_fields_from_excel",
    "extract_simple_dict_from_excel",
    "get_standard_excel_field_definitions",
]
