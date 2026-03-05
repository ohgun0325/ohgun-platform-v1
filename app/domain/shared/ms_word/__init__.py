"""Word(.docx) 문서 처리 모듈.

python-docx를 사용하여 .docx 파일에서 텍스트와 표를 추출합니다.

사용 예시:
    from app.domain.shared.ms_word import read_docx_text, read_docx_tables
    text = read_docx_text("document.docx")
    tables = read_docx_tables("document.docx")
"""

from app.domain.shared.ms_word.base import WordExtractionStrategy
from app.domain.shared.ms_word.word_reader import (
    DocxReader,
    read_docx_text,
    read_docx_tables,
)

__all__ = [
    "WordExtractionStrategy",
    "DocxReader",
    "read_docx_text",
    "read_docx_tables",
]
