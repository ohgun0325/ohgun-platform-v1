"""KOICA 보고서 요약 API.

PDF 업로드 → 훈련된 Exaone(LoRA)로 요약문 생성.
"""

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.domain.koica.services.report_summary_service import summarize_pdf_bytes

router = APIRouter(prefix="/report", tags=["koica-report"])


@router.post("/summarize")
async def report_summarize(file: UploadFile = File(...)):
    """PDF 파일을 업로드하면 KOICA 평가보고서 요약문을 반환합니다."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="PDF 파일만 업로드할 수 있습니다.")

    try:
        pdf_bytes = await file.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"파일 읽기 실패: {e}") from e

    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="빈 파일입니다.")

    try:
        summary = summarize_pdf_bytes(pdf_bytes)
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"요약 생성 중 오류: {e}") from e

    return {"summary": summary, "filename": file.filename}
