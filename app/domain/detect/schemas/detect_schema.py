"""인감도장/서명 검출 API 응답 스키마."""

from typing import List, Tuple

from pydantic import BaseModel, Field


class DetectionItem(BaseModel):
    """단일 검출 결과 (클래스, 신뢰도, 바운딩 박스)."""

    cls: str = Field(..., description="클래스명: stamp 또는 signature")
    conf: float = Field(..., ge=0, le=1, description="신뢰도 0~1")
    xyxy: Tuple[float, float, float, float] = Field(
        ...,
        description="바운딩 박스 [x1, y1, x2, y2]",
    )


class PageResult(BaseModel):
    """페이지별 검출 결과."""

    page_index: int = Field(..., ge=0, description="0-based 페이지 인덱스")
    has_stamp: bool = Field(..., description="인감도장 검출 여부")
    has_signature: bool = Field(..., description="서명 검출 여부")
    detections: List[DetectionItem] = Field(
        default_factory=list,
        description="해당 페이지의 검출 목록",
    )


class SummaryResult(BaseModel):
    """전체 요약 (문서 레벨)."""

    has_stamp_any: bool = Field(..., description="문서 내 인감도장 1개 이상 존재 여부")
    has_signature_any: bool = Field(..., description="문서 내 서명 1개 이상 존재 여부")
    stamp_pages: List[int] = Field(
        default_factory=list,
        description="인감도장이 검출된 페이지 인덱스 목록",
    )
    signature_pages: List[int] = Field(
        default_factory=list,
        description="서명이 검출된 페이지 인덱스 목록",
    )


class DetectResponse(BaseModel):
    """POST /api/v1/detect 응답."""

    job_id: str = Field(..., description="요청 식별자")
    filename: str = Field(..., description="업로드된 파일명")
    num_pages: int = Field(..., ge=0, description="총 페이지 수")
    summary: SummaryResult = Field(..., description="문서 요약")
    pages: List[PageResult] = Field(
        default_factory=list,
        description="페이지별 상세 결과",
    )
