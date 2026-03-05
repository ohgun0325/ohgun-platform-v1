"""Excel 필드 추출 API 라우터.

Excel 파일(.xlsx, .xls)을 업로드하면:
1. pandas로 시트를 읽고
2. 필드 정의에 따라 키워드 매칭 (문자열 + 임베딩)
3. (선택) Gemini로 형식 오류 보정
4. 템플릿 자동완성용 필드 추출 및 반환
"""

import logging
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from app.domain.shared.ms_excel.field_extractor import (
    extract_fields_from_excel,
    get_standard_excel_field_definitions,
)

router = APIRouter(prefix="/excel", tags=["excel"])
logger = logging.getLogger(__name__)


class ExcelField(BaseModel):
    """Excel에서 추출된 필드 정보."""
    value: str
    matched_keyword: str
    confidence: float
    location: Dict[str, int]  # {"row": int, "col": int}


class ExcelFieldExtractionResponse(BaseModel):
    """Excel 필드 추출 응답."""
    fields: Dict[str, ExcelField]
    metadata: Dict[str, Any]
    error: Optional[str] = None


class ExcelCorrectionItem(BaseModel):
    """Gemini 보정 1건."""
    field: str
    original: str
    corrected: str
    reason: str = ""


class ExcelExtractAndCorrectResponse(BaseModel):
    """Excel 추출 + Gemini 보정 응답."""
    fields: Dict[str, ExcelField]
    corrections: List[ExcelCorrectionItem] = []
    metadata: Dict[str, Any]
    used_gemini: bool = False
    error: Optional[str] = None


@router.post(
    "/extract-fields",
    response_model=ExcelFieldExtractionResponse,
    summary="Excel 필드 자동 추출",
    description=(
        "Excel 파일(.xlsx, .xls)을 업로드하면 표준 필드를 자동으로 추출합니다. "
        "문자열 매칭 실패 시 임베딩 기반 의미 매칭으로 폴백합니다. "
        "OCR 템플릿 자동완성과 동일한 방식으로 작동합니다."
    ),
)
async def extract_excel_fields(
    file: UploadFile = File(..., description="Excel 파일 (.xlsx, .xls)"),
    sheet_name: Optional[str] = None,
    use_semantic_matching: bool = True,
) -> ExcelFieldExtractionResponse:
    """Excel 파일에서 표준 필드를 추출합니다.
    
    Args:
        file: Excel 파일
        sheet_name: 시트 이름 (None이면 첫 시트)
        use_semantic_matching: 임베딩 기반 의미 매칭 사용 여부
    
    Returns:
        추출된 필드 정보
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="파일명이 비어 있습니다.")
    
    ext = Path(file.filename).suffix.lower()
    if ext not in (".xlsx", ".xls"):
        raise HTTPException(
            status_code=415,
            detail="Excel 파일(.xlsx, .xls)만 업로드할 수 있습니다.",
        )
    
    # 파일 읽기
    try:
        file_bytes = await file.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"파일 읽기 실패: {e}") from e
    
    if not file_bytes:
        raise HTTPException(status_code=400, detail="빈 파일입니다.")
    
    # 임시 파일 저장
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name
    
    try:
        logger.info(
            "[Excel API] 필드 추출 요청: file=%s, sheet=%s, semantic=%s",
            file.filename,
            sheet_name or "첫 시트",
            use_semantic_matching,
        )
        
        # 표준 필드 정의 가져오기
        field_defs = get_standard_excel_field_definitions()
        
        # 필드 추출
        result = extract_fields_from_excel(
            tmp_path,
            field_defs,
            sheet_name=sheet_name,
            use_semantic_matching=use_semantic_matching,
        )
        
        if result.get("error"):
            logger.error("[Excel API] 추출 실패: %s", result["error"])
            raise HTTPException(
                status_code=500,
                detail=f"Excel 필드 추출 실패: {result['error']}",
            )
        
        logger.info(
            "[Excel API] 추출 완료: fields=%d개, sheet=%s",
            len(result["fields"]),
            result["metadata"].get("sheet_name", ""),
        )
        
        return ExcelFieldExtractionResponse(
            fields=result["fields"],
            metadata=result["metadata"],
            error=None,
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("[Excel API] 예상치 못한 오류: %s", e)
        raise HTTPException(
            status_code=500,
            detail=f"Excel 처리 중 오류: {str(e)}",
        ) from e
    finally:
        # 임시 파일 삭제
        try:
            Path(tmp_path).unlink()
        except Exception:
            pass


@router.post(
    "/extract-and-correct",
    response_model=ExcelExtractAndCorrectResponse,
    summary="Excel 추출 + Gemini 보정",
    description=(
        "Excel 파일을 업로드하면 pandas로 필드를 추출한 뒤, "
        "Gemini가 형식 오류(날짜가 연락처에 들어감, 날짜·시간 붙어있는 형식 등)를 보정합니다. "
        "전체 과정이 터미널 로그에 출력됩니다."
    ),
)
async def extract_excel_and_correct(
    file: UploadFile = File(..., description="Excel 파일 (.xlsx, .xls)"),
    sheet_name: Optional[str] = None,
    use_semantic_matching: bool = True,
    use_gemini: bool = True,
) -> ExcelExtractAndCorrectResponse:
    """Excel 추출 후 Gemini로 보정까지 한 번에 실행합니다."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="파일명이 비어 있습니다.")

    ext = Path(file.filename).suffix.lower()
    if ext not in (".xlsx", ".xls"):
        raise HTTPException(
            status_code=415,
            detail="Excel 파일(.xlsx, .xls)만 업로드할 수 있습니다.",
        )

    try:
        file_bytes = await file.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"파일 읽기 실패: {e}") from e

    if not file_bytes:
        raise HTTPException(status_code=400, detail="빈 파일입니다.")

    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name

    try:
        logger.info(
            "[Excel API] 추출+보정 요청: file=%s, sheet=%s, use_gemini=%s",
            file.filename,
            sheet_name or "첫 시트",
            use_gemini,
        )
        print("[Excel API] 추출+보정 요청:", file.filename, "use_gemini=", use_gemini)

        gemini_model = None
        if use_gemini:
            try:
                from app.core.llm.gemini import get_chat_model
                gemini_model = get_chat_model()
                if gemini_model is None:
                    logger.warning("[Excel API] Gemini 로드 실패 → 보정 없이 추출만 수행")
            except Exception as e:
                logger.warning("[Excel API] Gemini 로드 예외: %s → 보정 없이 추출만 수행", e)

        from app.domain.shared.ms_excel.excel_gemini_pipeline import (
            run_excel_extract_and_correct,
        )

        result = run_excel_extract_and_correct(
            excel_path=tmp_path,
            field_definitions=None,
            sheet_name=sheet_name,
            use_semantic_matching=use_semantic_matching,
            gemini_model=gemini_model,
        )

        if result.get("error") and not result.get("fields"):
            logger.error("[Excel API] 추출+보정 실패: %s", result["error"])
            raise HTTPException(
                status_code=500,
                detail=result["error"] or "Excel 처리 실패",
            )

        raw_fields = result.get("raw_fields") or {}
        corrected_fields = result.get("fields") or {}
        fields_response: Dict[str, ExcelField] = {}
        for name, raw_data in raw_fields.items():
            if not isinstance(raw_data, dict):
                raw_data = {"value": str(raw_data), "matched_keyword": "", "confidence": 0.0, "location": {}}
            corrected_val = (corrected_fields.get(name) or {}).get("value", raw_data.get("value", ""))
            fields_response[name] = ExcelField(
                value=corrected_val,
                matched_keyword=raw_data.get("matched_keyword", ""),
                confidence=raw_data.get("confidence", 0.0),
                location=raw_data.get("location", {}),
            )
        for name in corrected_fields:
            if name not in fields_response:
                fields_response[name] = ExcelField(
                    value=(corrected_fields[name] or {}).get("value", ""),
                    matched_keyword="",
                    confidence=0.0,
                    location={},
                )

        corrections_response = [
            ExcelCorrectionItem(
                field=c.get("field", ""),
                original=str(c.get("original", ""))[:500],
                corrected=str(c.get("corrected", ""))[:500],
                reason=str(c.get("reason", ""))[:200],
            )
            for c in (result.get("corrections") or [])
        ]

        logger.info(
            "[Excel API] 추출+보정 완료: fields=%d개, corrections=%d건, used_gemini=%s",
            len(fields_response),
            len(corrections_response),
            result.get("used_gemini", False),
        )
        print(
            "[Excel API] 추출+보정 완료: fields=%d개, corrections=%d건, used_gemini=%s"
            % (len(fields_response), len(corrections_response), result.get("used_gemini", False))
        )

        return ExcelExtractAndCorrectResponse(
            fields=fields_response,
            corrections=corrections_response,
            metadata=result.get("metadata", {}),
            used_gemini=result.get("used_gemini", False),
            error=result.get("error"),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("[Excel API] 추출+보정 예외: %s", e)
        raise HTTPException(
            status_code=500,
            detail=f"Excel 추출/보정 중 오류: {str(e)}",
        ) from e
    finally:
        try:
            Path(tmp_path).unlink()
        except Exception:
            pass


@router.get(
    "/standard-fields",
    response_model=Dict[str, List[str]],
    summary="표준 Excel 필드 정의 조회",
    description="지원하는 표준 필드명과 키워드 목록을 반환합니다.",
)
async def get_standard_fields():
    """표준 Excel 필드 정의를 반환합니다."""
    field_defs = get_standard_excel_field_definitions()
    
    # keywords만 추출하여 반환
    return {
        field_name: definition["keywords"]
        for field_name, definition in field_defs.items()
    }
