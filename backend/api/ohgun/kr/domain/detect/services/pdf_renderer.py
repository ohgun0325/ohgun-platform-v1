"""PyMuPDF(fitz) 기반 PDF → 페이지별 이미지 렌더링.

- 메모리 기반 처리 기본 (파일 저장 없음).
- DPI 200~300 선택 가능, MAX_PAGES 제한.
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any, List, Optional, Union

# PIL Image (타입 힌트용)
try:
    from PIL import Image
    PIL_Image = Image.Image
except ImportError:
    PIL_Image = None  # type: ignore


def render_pdf_to_images(
    pdf_source: Union[bytes, Path, str],
    dpi: int = 250,
    max_pages: int = 50,
    save_debug_dir: Optional[Path] = None,
) -> List["PIL_Image"]:
    """PDF를 페이지별 PIL Image 리스트로 렌더링합니다.

    Args:
        pdf_source: PDF 바이트, 또는 파일 경로(Path/str).
        dpi: 렌더링 DPI (200~300 권장, 기본 250).
        max_pages: 처리할 최대 페이지 수. 초과 시 마지막 페이지까지 무시.
        save_debug_dir: 지정 시 각 페이지 이미지를 저장 (디버그용).

    Returns:
        페이지 순서의 PIL Image 리스트. 0-based 인덱스 = page_index.

    Raises:
        ValueError: PDF가 비어 있거나, 페이지 수가 0인 경우.
        RuntimeError: 페이지 수가 max_pages 초과.
    """
    import fitz  # PyMuPDF  # type: ignore[import-untyped]

    if dpi < 200 or dpi > 300:
        dpi = max(200, min(300, dpi))

    if isinstance(pdf_source, (Path, str)):
        doc = fitz.open(str(pdf_source))
        from_file = True
    else:
        if not pdf_source:
            raise ValueError("PDF 바이트가 비어 있습니다.")
        doc = fitz.open(stream=pdf_source, filetype="pdf")
        from_file = False

    try:
        num_pages = len(doc)
        if num_pages == 0:
            raise ValueError("PDF에 페이지가 없습니다.")
        if num_pages > max_pages:
            raise RuntimeError(
                f"페이지 수({num_pages})가 최대 허용({max_pages})을 초과합니다. "
                "MAX_PAGES 환경변수로 조정할 수 있습니다."
            )

        images: List["PIL_Image"] = []
        for page_index in range(num_pages):
            page = doc[page_index]
            mat = fitz.Matrix(dpi / 72, dpi / 72)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            img = _pixmap_to_pil(pix)
            images.append(img)

            if save_debug_dir:
                save_debug_dir = Path(save_debug_dir)
                save_debug_dir.mkdir(parents=True, exist_ok=True)
                img.save(save_debug_dir / f"page_{page_index:04d}.png")

        return images
    finally:
        doc.close()


def _pixmap_to_pil(pix: Any) -> "PIL_Image":
    """fitz.Pixmap → PIL.Image (RGB)."""
    from PIL import Image
    import fitz  # type: ignore[import-untyped]

    # fitz Pixmap to bytes (RGB)
    if pix.alpha:
        pix = fitz.Pixmap(fitz.csRGB, pix)
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    return img
