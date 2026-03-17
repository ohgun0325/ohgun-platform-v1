"""글자 인식 OCR API.

POST /api/v1/ocr:
    - 이미지(PNG/JPG) 업로드 → EasyOCR로 텍스트 추출 후 full_text, items 반환.

POST /api/v1/ocr/with-llm:
    - 이미지 → EasyOCR → Exaone LLM 보정 → 보정 텍스트 + 구조화 필드 반환.
"""

import asyncio
import io
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from pydantic import BaseModel

router = APIRouter(prefix="/ocr", tags=["ocr"])
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def _convert_pdf_to_image_bytes(pdf_bytes: bytes, dpi: int = 250) -> bytes:
    """PDF 바이트를 단일 페이지 이미지(PNG) 바이트로 변환.

    - 기본적으로 첫 번째 페이지만 사용 (테스트/양식 문서 기준 일반적인 케이스)
    - PyMuPDF로 렌더링 후 PNG로 인코딩
    """
    try:
        import fitz  # type: ignore
        from PIL import Image
    except ImportError as e:  # pragma: no cover - 환경 의존
        raise RuntimeError(
            "PDF를 이미지로 변환하려면 'PyMuPDF'와 'Pillow'가 필요합니다. "
            "pip install PyMuPDF Pillow"
        ) from e

    if not pdf_bytes:
        raise ValueError("빈 PDF 바이트입니다.")

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        if doc.page_count < 1:
            raise ValueError("PDF에 페이지가 없습니다.")

        page = doc[0]
        mat = fitz.Matrix(dpi / 72, dpi / 72)
        pix = page.get_pixmap(matrix=mat, alpha=False)

        if pix.alpha:  # RGB로 변환
            pix = fitz.Pixmap(fitz.csRGB, pix)

        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
    finally:
        doc.close()


class OcrItem(BaseModel):
    text: str
    confidence: float


class OcrResponse(BaseModel):
    full_text: str
    items: List[OcrItem]


class OcrWithLlmCorrection(BaseModel):
    original: str
    corrected: str


class OcrField(BaseModel):
    value: str = ""
    evidence_text: str = ""
    confidence: float = 0.0


class OcrWithLlmResponse(BaseModel):
    """OCR + LLM 파이프라인 응답."""
    raw_full_text: str
    raw_items: List[OcrItem]
    corrected_text: Optional[str] = None
    # 필드명 → {value, evidence_text, confidence}
    fields: Dict[str, OcrField] = {}
    corrections: List[OcrWithLlmCorrection] = []
    used_llm: bool = False
    error: Optional[str] = None


def _init_ocr_reader():
    """EasyOCR Reader 싱글톤 생성 (스레드에서 호출)."""
    from domain.shared.ocr import EasyOCRReader
    return EasyOCRReader(languages=["ko", "en"], gpu=True)


def _run_ocr_sync(reader, image_bytes: bytes) -> tuple[str, list[tuple[str, float]]]:
    """동기 OCR 실행 (이벤트 루프 블로킹 방지를 위해 스레드에서 호출)."""
    import numpy as np
    from PIL import Image

    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    img_array = np.array(img)
    results = reader.reader.readtext(img_array)
    items = [(text, float(conf)) for (_, text, conf) in results]
    full_text = " ".join(t for t, _ in items)
    return full_text, items


@router.post(
    "",
    response_model=OcrResponse,
    summary="글자 인식 OCR (이미지/PDF)",
    description="이미지(PNG/JPG) 또는 PDF를 업로드하면 EasyOCR로 텍스트를 추출하여 반환합니다. PDF는 첫 페이지를 이미지로 변환하여 사용합니다.",
)
async def run_ocr(
    request: Request,
    file: UploadFile = File(..., description="이미지 파일 (PNG, JPG, JPEG) 또는 PDF 파일"),
) -> OcrResponse:
    if not file.filename:
        raise HTTPException(status_code=400, detail="파일명이 비어 있습니다.")
    ext = Path(file.filename).suffix.lower()
    if ext not in (".png", ".jpg", ".jpeg", ".pdf"):
        raise HTTPException(
            status_code=415,
            detail="이미지 파일(.png, .jpg, .jpeg) 또는 PDF(.pdf)만 업로드할 수 있습니다.",
        )
    try:
        file_bytes = await file.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"파일 읽기 실패: {e}") from e
    if not file_bytes:
        raise HTTPException(status_code=400, detail="빈 파일입니다.")

    # PDF인 경우 → 첫 페이지를 이미지로 변환
    if ext == ".pdf":
        try:
            image_bytes = _convert_pdf_to_image_bytes(file_bytes)
        except Exception as e:
            logger.exception("[OCR API] PDF → 이미지 변환 실패: %s", e)
            raise HTTPException(
                status_code=400,
                detail=f"PDF를 이미지로 변환하는 중 오류가 발생했습니다: {getattr(e, 'message', str(e))}",
            ) from e
    else:
        image_bytes = file_bytes

    # Lazy init: 첫 요청 시 Reader 생성 후 캐시
    reader = getattr(request.app.state, "ocr_reader", None)
    if reader is None:
        try:
            reader = await asyncio.to_thread(_init_ocr_reader)
            request.app.state.ocr_reader = reader
        except Exception as e:
            raise HTTPException(
                status_code=503,
                detail=f"OCR 모델 로드 실패: {getattr(e, 'message', str(e))}",
            ) from e

    logger.info("[OCR API] POST /ocr 요청: 파일=%s, 크기=%d bytes", file.filename, len(image_bytes))
    try:
        full_text, items = await asyncio.to_thread(_run_ocr_sync, reader, image_bytes)
    except Exception as e:
        logger.exception("[OCR API] OCR 실행 실패: %s", e)
        raise HTTPException(
            status_code=500,
            detail=f"OCR 처리 중 오류: {getattr(e, 'message', str(e))}",
        ) from e

    logger.info("[OCR API] POST /ocr 완료: 항목 %d개, full_text %d자", len(items), len(full_text))
    return OcrResponse(
        full_text=full_text,
        items=[OcrItem(text=t, confidence=c) for t, c in items],
    )


@router.post(
    "/with-llm",
    response_model=OcrWithLlmResponse,
    summary="OCR + LLM 보정",
    description="이미지(PNG/JPG) 또는 PDF를 EasyOCR로 인식한 뒤 Gemini LLM으로 누락/오타를 보정합니다. use_llm=false면 OCR만 수행해 빠르게 반환합니다. PDF는 첫 페이지를 이미지로 변환하여 사용합니다.",
)
async def run_ocr_with_llm(
    request: Request,
    file: UploadFile = File(..., description="이미지 파일 (PNG, JPG, JPEG) 또는 PDF 파일"),
    use_llm: bool = True,
) -> OcrWithLlmResponse:
    if not file.filename:
        raise HTTPException(status_code=400, detail="파일명이 비어 있습니다.")
    ext = Path(file.filename).suffix.lower()
    if ext not in (".png", ".jpg", ".jpeg", ".pdf"):
        raise HTTPException(
            status_code=415,
            detail="이미지 파일(.png, .jpg, .jpeg) 또는 PDF(.pdf)만 업로드할 수 있습니다.",
        )
    try:
        file_bytes = await file.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"파일 읽기 실패: {e}") from e
    if not file_bytes:
        raise HTTPException(status_code=400, detail="빈 파일입니다.")

    # PDF인 경우 → 첫 페이지를 이미지로 변환
    if ext == ".pdf":
        try:
            image_bytes = _convert_pdf_to_image_bytes(file_bytes)
        except Exception as e:
            logger.exception("[OCR API] PDF → 이미지 변환 실패: %s", e)
            raise HTTPException(
                status_code=400,
                detail=f"PDF를 이미지로 변환하는 중 오류가 발생했습니다: {getattr(e, 'message', str(e))}",
            ) from e
    else:
        image_bytes = file_bytes

    reader = getattr(request.app.state, "ocr_reader", None)
    if reader is None:
        try:
            reader = await asyncio.to_thread(_init_ocr_reader)
            request.app.state.ocr_reader = reader
        except Exception as e:
            raise HTTPException(
                status_code=503,
                detail=f"OCR 모델 로드 실패: {getattr(e, 'message', str(e))}",
            ) from e

    chat_model = getattr(request.app.state, "chat_model", None)

    # ✅ OCR 보정용 LLM은 **항상 Gemini만** 사용 (Exaone는 사용하지 않음)
    llm_model: Any = None
    if use_llm:
        # 1) app.state.chat_model이 Gemini라면 그대로 사용
        if chat_model is not None and hasattr(chat_model, "__class__"):
            class_name = chat_model.__class__.__name__
            if "Gemini" in class_name or "Google" in class_name:
                llm_model = chat_model
                logger.info("[OCR API] chat_model=Gemini 감지 → Gemini 사용")

        # 2) 아니라면 (예: Exaone 등) 무시하고 Gemini를 직접 로드
        if llm_model is None:
            try:
                from core.llm.gemini import get_chat_model as get_gemini

                gemini = get_gemini()
                if gemini:
                    llm_model = gemini
                    logger.info("[OCR API] Gemini API 직접 로드 성공")
                else:
                    logger.warning("[OCR API] Gemini 모델을 로드하지 못했습니다. use_llm=False로 동작합니다.")
            except Exception as e:
                logger.warning("[OCR API] Gemini 로드 실패: %s", e)

    logger.info(
        "[OCR API] POST /ocr/with-llm 요청: 파일=%s, 크기=%d bytes, use_llm=%s, LLM 사용=%s",
        file.filename,
        len(image_bytes),
        use_llm,
        "예" if llm_model else "아니오(모델 없음/미로드)",
    )
    try:
        from domain.shared.ocr.ocr_llm_pipeline import run_pipeline
        result: Dict[str, Any] = await asyncio.to_thread(
            run_pipeline, reader, image_bytes, llm_model
        )
    except Exception as e:
        logger.exception("[OCR API] OCR/LLM 파이프라인 실패: %s", e)
        raise HTTPException(
            status_code=500,
            detail=f"OCR/LLM 처리 중 오류: {getattr(e, 'message', str(e))}",
        ) from e

    used_llm = result.get("used_llm", False)
    logger.info(
        "[OCR API] POST /ocr/with-llm 완료: used_llm=%s, corrections=%d, fields 개수=%d",
        used_llm,
        len(result.get("corrections", [])),
        len(result.get("fields", {})),
    )
    if use_llm and not used_llm:
        logger.warning(
            "[OCR API] LLM 보정이 적용되지 않았습니다. "
            "Gemini API 키 및 모델 설정(GEMINI_MODEL)을 확인하세요. "
            "현재 화면에 보이는 값은 OCR 전처리 결과만 포함할 수 있습니다."
        )

    raw_items = [
        OcrItem(text=x.get("text", ""), confidence=float(x.get("confidence", 0)))
        for x in result.get("raw_items", [])
    ]
    corrections = [
        OcrWithLlmCorrection(original=c.get("original", ""), corrected=c.get("corrected", ""))
        for c in result.get("corrections", [])
    ]
    return OcrWithLlmResponse(
        raw_full_text=result.get("raw_full_text", ""),
        raw_items=raw_items,
        corrected_text=result.get("corrected_text"),
        fields=result.get("fields", {}),
        corrections=corrections,
        used_llm=result.get("used_llm", False),
        error=result.get("error"),
    )
