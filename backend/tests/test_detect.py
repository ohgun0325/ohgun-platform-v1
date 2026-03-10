"""인감도장/서명 검출 API 및 서비스 유닛 테스트.

- 샘플 PDF가 없어도 mock 기반으로 검증.
- 실행: pytest tests/test_detect.py -v
"""

import io
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# PDF 렌더링: fitz mock으로 페이지 수·이미지 반환 검증
def test_render_pdf_to_images_mock():
    """render_pdf_to_images가 fitz로 열고 페이지 수만큼 이미지를 반환하는지 (mock)."""
    import sys
    from PIL import Image
    import numpy as np

    fake_img = Image.fromarray(np.zeros((100, 100, 3), dtype=np.uint8))
    mock_fitz = MagicMock()
    doc = MagicMock()
    doc.__len__ = lambda self: 2
    doc.close = MagicMock()

    def get_pixmap(*args, **kwargs):
        pix = MagicMock()
        pix.width = 100
        pix.height = 100
        pix.alpha = False
        pix.samples = b"\x00" * (100 * 100 * 3)
        return pix

    page = MagicMock()
    page.get_pixmap = get_pixmap
    doc.__getitem__ = lambda self, i: page
    mock_fitz.open.return_value = doc
    mock_fitz.Matrix.return_value = MagicMock()

    with patch.dict(sys.modules, {"fitz": mock_fitz}):
        with patch("app.domain.detect.services.pdf_renderer._pixmap_to_pil", return_value=fake_img):
            from app.domain.detect.services.pdf_renderer import render_pdf_to_images
            pdf_bytes = b"%PDF-1.4 dummy"
            images = render_pdf_to_images(pdf_bytes, dpi=250, max_pages=50)
            assert len(images) == 2
            assert all(hasattr(img, "size") for img in images)


def test_detect_endpoint_rejects_non_pdf():
    """POST /api/v1/detect 에 비PDF 업로드 시 415."""
    # 앱을 직접 생성하고 detect_router만 포함 (lifespan 없이, stamp_detector 없음)
    from fastapi import FastAPI
    from app.api.v1.detect.detect_router import router as detect_router

    app = FastAPI()
    app.include_router(detect_router, prefix="/api/v1")
    app.state.stamp_detector = None

    client = TestClient(app)
    response = client.post(
        "/api/v1/detect",
        files={"file": ("test.txt", io.BytesIO(b"not a pdf"), "text/plain")},
    )
    assert response.status_code == 415


def test_detect_endpoint_503_when_model_not_loaded():
    """모델 미로드 시 PDF 업로드해도 503."""
    from fastapi import FastAPI
    from app.api.v1.detect.detect_router import router as detect_router

    app = FastAPI()
    app.include_router(detect_router, prefix="/api/v1")
    app.state.stamp_detector = None

    client = TestClient(app)
    # 최소한의 PDF 시그니처만 있는 바이트
    pdf_like = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\nxref\n0 0\ntrailer\n<<>>\nstartxref\n0\n%%EOF"
    response = client.post(
        "/api/v1/detect",
        files={"file": ("sample.pdf", io.BytesIO(pdf_like), "application/pdf")},
    )
    # detector가 None이면 503 반환 (렌더링 전에 검사)
    assert response.status_code == 503
