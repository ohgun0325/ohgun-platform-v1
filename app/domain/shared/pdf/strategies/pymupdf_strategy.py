"""PyMuPDF(fitz) 기반 PDF 추출 전략.

- 빠른 텍스트 추출
- 이미지 렌더링 (YOLO 등에 사용)
- 메타데이터 추출
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import List, Dict, Any, Union, Optional

try:
    import fitz  # PyMuPDF
except ImportError:
    raise ImportError("PyMuPDF가 설치되지 않았습니다. pip install PyMuPDF")

try:
    from PIL import Image
    PIL_Image = Image.Image
except ImportError:
    PIL_Image = None

from app.domain.shared.pdf.strategies.pdf_strategy import PDFExtractionStrategy


class PyMuPDFStrategy(PDFExtractionStrategy):
    """PyMuPDF(fitz)를 사용한 PDF 추출 전략."""
    
    def __init__(self, extract_images: bool = False):
        """
        Args:
            extract_images: 이미지 추출 여부
        """
        self.extract_images = extract_images
    
    def extract(self, file_path: str) -> str:
        """PDF에서 텍스트를 추출합니다.
        
        Args:
            file_path: PDF 파일 경로
            
        Returns:
            추출된 텍스트
        """
        doc = fitz.open(file_path)
        try:
            text_parts = []
            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text()
                if text.strip():
                    text_parts.append(f"[Page {page_num + 1}]\n{text}")
            
            return "\n\n".join(text_parts)
        finally:
            doc.close()
    
    def extract_pages(
        self, 
        pdf_source: Union[str, Path, bytes]
    ) -> List[Dict[str, Any]]:
        """PDF의 모든 페이지를 개별적으로 추출합니다.
        
        Args:
            pdf_source: PDF 파일 경로 또는 바이트 데이터
            
        Returns:
            페이지별 데이터 리스트
        """
        if isinstance(pdf_source, bytes):
            doc = fitz.open(stream=pdf_source, filetype="pdf")
        else:
            doc = fitz.open(str(pdf_source))
        
        try:
            pages_data = []
            for page_num in range(len(doc)):
                page = doc[page_num]
                
                page_data = {
                    "page_num": page_num + 1,
                    "text": page.get_text(),
                    "metadata": {
                        "width": page.rect.width,
                        "height": page.rect.height,
                        "rotation": page.rotation,
                    }
                }
                
                if self.extract_images:
                    page_data["image_count"] = len(page.get_images())
                
                pages_data.append(page_data)
            
            return pages_data
        finally:
            doc.close()
    
    def extract_text_from_page(
        self, 
        pdf_source: Union[str, Path, bytes], 
        page_num: int
    ) -> str:
        """특정 페이지에서 텍스트만 추출합니다.
        
        Args:
            pdf_source: PDF 파일 경로 또는 바이트 데이터
            page_num: 페이지 번호 (1-based)
            
        Returns:
            추출된 텍스트
        """
        if isinstance(pdf_source, bytes):
            doc = fitz.open(stream=pdf_source, filetype="pdf")
        else:
            doc = fitz.open(str(pdf_source))
        
        try:
            if page_num < 1 or page_num > len(doc):
                raise ValueError(f"페이지 번호 {page_num}이 범위를 벗어났습니다.")
            
            page = doc[page_num - 1]  # 0-based 인덱스
            return page.get_text()
        finally:
            doc.close()
    
    def get_page_count(self, pdf_source: Union[str, Path, bytes]) -> int:
        """PDF의 총 페이지 수를 반환합니다.
        
        Args:
            pdf_source: PDF 파일 경로 또는 바이트 데이터
            
        Returns:
            페이지 수
        """
        if isinstance(pdf_source, bytes):
            doc = fitz.open(stream=pdf_source, filetype="pdf")
        else:
            doc = fitz.open(str(pdf_source))
        
        try:
            return len(doc)
        finally:
            doc.close()
    
    def get_metadata(self, pdf_source: Union[str, Path, bytes]) -> Dict[str, Any]:
        """PDF 메타데이터를 추출합니다.
        
        Args:
            pdf_source: PDF 파일 경로 또는 바이트 데이터
            
        Returns:
            메타데이터 딕셔너리
        """
        if isinstance(pdf_source, bytes):
            doc = fitz.open(stream=pdf_source, filetype="pdf")
        else:
            doc = fitz.open(str(pdf_source))
        
        try:
            metadata = doc.metadata.copy()
            metadata["page_count"] = len(doc)
            return metadata
        finally:
            doc.close()
    
    def render_page_to_image(
        self,
        pdf_source: Union[str, Path, bytes],
        page_num: int,
        dpi: int = 250,
    ) -> "PIL_Image":
        """특정 페이지를 이미지로 렌더링합니다.
        
        Args:
            pdf_source: PDF 파일 경로 또는 바이트 데이터
            page_num: 페이지 번호 (1-based)
            dpi: 렌더링 DPI (기본: 250)
            
        Returns:
            PIL Image 객체
        """
        from PIL import Image
        
        if isinstance(pdf_source, bytes):
            doc = fitz.open(stream=pdf_source, filetype="pdf")
        else:
            doc = fitz.open(str(pdf_source))
        
        try:
            if page_num < 1 or page_num > len(doc):
                raise ValueError(f"페이지 번호 {page_num}이 범위를 벗어났습니다.")
            
            page = doc[page_num - 1]
            mat = fitz.Matrix(dpi / 72, dpi / 72)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            
            # Pixmap을 PIL Image로 변환
            if pix.alpha:
                pix = fitz.Pixmap(fitz.csRGB, pix)
            
            img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            return img
        finally:
            doc.close()
    
    def render_all_pages_to_images(
        self,
        pdf_source: Union[str, Path, bytes],
        dpi: int = 250,
        max_pages: int = 50,
    ) -> List["PIL_Image"]:
        """모든 페이지를 이미지로 렌더링합니다.
        
        Args:
            pdf_source: PDF 파일 경로 또는 바이트 데이터
            dpi: 렌더링 DPI (기본: 250)
            max_pages: 최대 페이지 수
            
        Returns:
            PIL Image 리스트
        """
        from PIL import Image
        
        if isinstance(pdf_source, bytes):
            doc = fitz.open(stream=pdf_source, filetype="pdf")
        else:
            doc = fitz.open(str(pdf_source))
        
        try:
            num_pages = len(doc)
            if num_pages == 0:
                raise ValueError("PDF에 페이지가 없습니다.")
            if num_pages > max_pages:
                raise RuntimeError(
                    f"페이지 수({num_pages})가 최대 허용({max_pages})을 초과합니다."
                )
            
            images = []
            for page_num in range(num_pages):
                page = doc[page_num]
                mat = fitz.Matrix(dpi / 72, dpi / 72)
                pix = page.get_pixmap(matrix=mat, alpha=False)
                
                if pix.alpha:
                    pix = fitz.Pixmap(fitz.csRGB, pix)
                
                img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
                images.append(img)
            
            return images
        finally:
            doc.close()


class PyMuPDFImageExtractor:
    """이미지 추출에 특화된 PyMuPDF 래퍼 클래스."""
    
    def extract_images_from_page(
        self,
        pdf_source: Union[str, Path, bytes],
        page_num: int,
    ) -> List[Dict[str, Any]]:
        """특정 페이지에서 이미지를 추출합니다.
        
        Args:
            pdf_source: PDF 파일 경로 또는 바이트 데이터
            page_num: 페이지 번호 (1-based)
            
        Returns:
            이미지 정보 리스트. 각 항목은:
            {
                "xref": int,  # 이미지 참조 번호
                "bbox": (x0, y0, x1, y1),  # 바운딩 박스
                "width": int,
                "height": int,
                "ext": str,  # 확장자 (png, jpeg 등)
                "image": PIL.Image  # PIL Image 객체
            }
        """
        from PIL import Image
        
        if isinstance(pdf_source, bytes):
            doc = fitz.open(stream=pdf_source, filetype="pdf")
        else:
            doc = fitz.open(str(pdf_source))
        
        try:
            if page_num < 1 or page_num > len(doc):
                raise ValueError(f"페이지 번호 {page_num}이 범위를 벗어났습니다.")
            
            page = doc[page_num - 1]
            images_info = []
            
            for img_index, img in enumerate(page.get_images()):
                xref = img[0]
                base_image = doc.extract_image(xref)
                
                image_bytes = base_image["image"]
                image_ext = base_image["ext"]
                
                # PIL Image로 변환
                pil_image = Image.open(io.BytesIO(image_bytes))
                
                # 이미지 위치 정보 가져오기
                img_rects = page.get_image_rects(xref)
                bbox = img_rects[0] if img_rects else (0, 0, 0, 0)
                
                images_info.append({
                    "xref": xref,
                    "bbox": bbox,
                    "width": pil_image.width,
                    "height": pil_image.height,
                    "ext": image_ext,
                    "image": pil_image,
                })
            
            return images_info
        finally:
            doc.close()
