"""입찰서류 인감도장/서명 검출 API.

POST /api/v1/detect:
    - PDF 업로드 → 페이지별 stamp/signature 유무 + 좌표 + 신뢰도.
    - PNG/JPG 업로드 → 단일 페이지 이미지로 처리 (page_index=0).
"""

import uuid
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from PIL import Image
import io

from app.core.config import settings
from app.domain.detect.schemas.detect_schema import (
    DetectionItem,
    DetectResponse,
    PageResult,
    SummaryResult,
)
from app.domain.detect.services.pdf_renderer import render_pdf_to_images
from app.domain.detect.services.stamp_detector import StampDetector

router = APIRouter(prefix="/detect", tags=["detect"])


def _get_detector(request: Request) -> Optional[StampDetector]:
    """앱 상태에서 StampDetector 인스턴스를 반환합니다."""
    return getattr(request.app.state, "stamp_detector", None)


@router.post(
    "",
    response_model=DetectResponse,
    summary="인감도장/서명 검출",
    description=(
        "PDF, PNG, JPG 파일 1개를 업로드하면 페이지별(또는 단일 이미지의 경우 1페이지) "
        "인감도장(stamp)과 서명(signature) 존재 여부 및 검출 좌표·신뢰도를 반환합니다."
    ),
)
async def detect_stamps(
    request: Request,
    file: UploadFile = File(
        ...,
        description="PDF 또는 이미지 파일 (PDF/PNG/JPG)",
    ),
) -> DetectResponse:
    """PDF 또는 이미지에서 인감도장/서명 검출. 모델 미로드 시 503."""
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="파일명이 비어 있습니다.",
        )

    filename_lower = file.filename.lower()
    is_pdf = filename_lower.endswith(".pdf")
    is_image = filename_lower.endswith((".png", ".jpg", ".jpeg"))

    if not (is_pdf or is_image):
        raise HTTPException(
            status_code=415,
            detail="PDF(.pdf) 또는 이미지(.png, .jpg, .jpeg)만 업로드할 수 있습니다.",
        )

    try:
        file_bytes = await file.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"파일 읽기 실패: {e}") from e

    if not file_bytes:
        raise HTTPException(status_code=400, detail="빈 파일입니다.")

    detector = _get_detector(request)
    if detector is None or not detector.is_loaded:
        raise HTTPException(
            status_code=503,
            detail="검출 모델이 로드되지 않았습니다. YOLO_MODEL_PATH를 확인하세요.",
        )

    job_id = str(uuid.uuid4())

    # 입력 타입에 따라 PIL 이미지 리스트 준비
    images: List["Image.Image"] = []
    save_debug_dir: Optional[Path] = Path("debug_stamp_pages") if settings.save_debug_images else None

    if is_pdf:
        # 기존 PDF 경로 유지
        try:
            images = render_pdf_to_images(
                file_bytes,
                dpi=settings.render_dpi,
                max_pages=settings.max_pages,
                save_debug_dir=save_debug_dir,
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        except RuntimeError as e:
            raise HTTPException(status_code=413, detail=str(e)) from e
    else:
        # 단일 이미지(PNG/JPG)를 PIL Image로 로드
        try:
            img = Image.open(io.BytesIO(file_bytes)).convert("RGB")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"이미지 디코딩 실패: {e}") from e

        images = [img]

        # 디버그 이미지 저장 옵션
        if save_debug_dir:
            save_debug_dir = Path(save_debug_dir)
            save_debug_dir.mkdir(parents=True, exist_ok=True)
            img.save(save_debug_dir / "page_0000.png")

    num_pages = len(images)
    pages_results: List[PageResult] = []
    stamp_pages: List[int] = []
    signature_pages: List[int] = []

    # 페이지 루프: 직렬 처리. 확장 시 ThreadPoolExecutor 등으로 병렬화 가능.
    for page_index, img in enumerate(images):
        raw_detections = detector.predict(img)
        detections = [
            DetectionItem(cls=cls, conf=round(conf, 4), xyxy=(xyxy[0], xyxy[1], xyxy[2], xyxy[3]))
            for cls, conf, xyxy in raw_detections
        ]
        has_stamp = detector.has_stamp(raw_detections)
        has_signature = detector.has_signature(raw_detections)
        if has_stamp:
            stamp_pages.append(page_index)
        if has_signature:
            signature_pages.append(page_index)
        pages_results.append(
            PageResult(
                page_index=page_index,
                has_stamp=has_stamp,
                has_signature=has_signature,
                detections=detections,
            )
        )

    summary = SummaryResult(
        has_stamp_any=len(stamp_pages) > 0,
        has_signature_any=len(signature_pages) > 0,
        stamp_pages=stamp_pages,
        signature_pages=signature_pages,
    )

    return DetectResponse(
        job_id=job_id,
        filename=file.filename or "unknown.pdf",
        num_pages=num_pages,
        summary=summary,
        pages=pages_results,
    )
