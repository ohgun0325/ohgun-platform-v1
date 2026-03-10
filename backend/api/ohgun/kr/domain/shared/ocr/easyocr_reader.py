"""
EasyOCR Reader
GPU 가속 OCR 텍스트 추출
"""

import easyocr
import numpy as np
from typing import List, Tuple, Optional
from pathlib import Path

# 프로젝트 루트 기준 models/easyocr 경로 (모델 저장/로드)
# ocr -> shared -> domain -> app -> langchain (5단계 상위)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
EASYOCR_MODEL_DIR = _PROJECT_ROOT / "models" / "easyocr"


class EasyOCRReader:
    """
    EasyOCR 기반 텍스트 인식 클래스
    
    Features:
    - GPU 가속 지원 (RTX 3070 Ti 최적화)
    - 한국어 + 영어 동시 인식
    - 이미지 파일 및 NumPy 배열 입력 지원
    - 신뢰도 기반 필터링
    """
    
    def __init__(
        self,
        languages: List[str] = None,
        gpu: bool = True,
        verbose: bool = False,
        model_storage_directory: Optional[str | Path] = None
    ):
        """
        EasyOCR 리더 초기화
        
        Args:
            languages: 인식할 언어 리스트 (기본값: ['ko', 'en'])
            gpu: GPU 사용 여부 (기본값: True)
            verbose: 상세 로그 출력 여부 (기본값: False)
            model_storage_directory: 모델 저장/로드 경로 (기본값: 프로젝트 models/easyocr)
        """
        if languages is None:
            languages = ['ko', 'en']
        
        model_dir = model_storage_directory if model_storage_directory is not None else EASYOCR_MODEL_DIR
        model_dir = Path(model_dir).resolve()
        model_dir.mkdir(parents=True, exist_ok=True)
        
        self.languages = languages
        self.gpu = gpu
        self.model_storage_directory = model_dir
        self.reader = easyocr.Reader(
            languages,
            gpu=gpu,
            verbose=verbose,
            model_storage_directory=str(model_dir)
        )
    
    def read_image(
        self,
        image_path: str | Path
    ) -> List[Tuple[List, str, float]]:
        """
        이미지 파일에서 텍스트 추출
        
        Args:
            image_path: 이미지 파일 경로
            
        Returns:
            List[(bbox, text, confidence)]
            - bbox: [[x1,y1], [x2,y2], [x3,y3], [x4,y4]] 형태의 좌표
            - text: 인식된 텍스트
            - confidence: 신뢰도 (0.0 ~ 1.0)
            
        Example:
            >>> ocr = EasyOCRReader()
            >>> result = ocr.read_image('document.jpg')
            >>> for bbox, text, conf in result:
            ...     print(f"{text}: {conf:.2%}")
        """
        image_path = str(image_path)
        result = self.reader.readtext(image_path)
        return result
    
    def read_image_array(
        self,
        image: np.ndarray
    ) -> List[Tuple[List, str, float]]:
        """
        NumPy 배열 이미지에서 텍스트 추출
        
        Args:
            image: NumPy 배열 이미지 (OpenCV, PIL 등에서 로드한 이미지)
            
        Returns:
            List[(bbox, text, confidence)]
            
        Example:
            >>> import cv2
            >>> ocr = EasyOCRReader()
            >>> img = cv2.imread('document.jpg')
            >>> result = ocr.read_image_array(img)
        """
        result = self.reader.readtext(image)
        return result
    
    def extract_text_only(
        self,
        image_path: str | Path | np.ndarray,
        min_confidence: float = 0.5
    ) -> List[str]:
        """
        이미지에서 텍스트만 추출 (신뢰도 필터링)
        
        Args:
            image_path: 이미지 파일 경로 또는 NumPy 배열
            min_confidence: 최소 신뢰도 (0.0 ~ 1.0)
            
        Returns:
            텍스트 리스트
            
        Example:
            >>> ocr = EasyOCRReader()
            >>> texts = ocr.extract_text_only('document.jpg', min_confidence=0.7)
            >>> print(' '.join(texts))
        """
        if isinstance(image_path, np.ndarray):
            result = self.read_image_array(image_path)
        else:
            result = self.read_image(image_path)
        
        texts = [
            text
            for _, text, confidence in result
            if confidence >= min_confidence
        ]
        return texts
    
    def extract_with_position(
        self,
        image_path: str | Path | np.ndarray,
        min_confidence: float = 0.5
    ) -> List[dict]:
        """
        이미지에서 텍스트와 위치 정보를 함께 추출
        
        Args:
            image_path: 이미지 파일 경로 또는 NumPy 배열
            min_confidence: 최소 신뢰도
            
        Returns:
            List[dict]: 텍스트 정보 딕셔너리 리스트
            - text: 인식된 텍스트
            - confidence: 신뢰도
            - bbox: 좌표 [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
            - center: 중심 좌표 (x, y)
            
        Example:
            >>> ocr = EasyOCRReader()
            >>> results = ocr.extract_with_position('document.jpg')
            >>> for item in results:
            ...     print(f"{item['text']} at {item['center']}")
        """
        if isinstance(image_path, np.ndarray):
            result = self.read_image_array(image_path)
        else:
            result = self.read_image(image_path)
        
        processed = []
        for bbox, text, confidence in result:
            if confidence >= min_confidence:
                # 중심점 계산
                center_x = sum(point[0] for point in bbox) / 4
                center_y = sum(point[1] for point in bbox) / 4
                
                processed.append({
                    'text': text,
                    'confidence': confidence,
                    'bbox': bbox,
                    'center': (center_x, center_y)
                })
        
        return processed
    
    def extract_full_text(
        self,
        image_path: str | Path | np.ndarray,
        min_confidence: float = 0.5,
        separator: str = ' '
    ) -> str:
        """
        이미지에서 전체 텍스트를 하나의 문자열로 추출
        
        Args:
            image_path: 이미지 파일 경로 또는 NumPy 배열
            min_confidence: 최소 신뢰도
            separator: 텍스트 구분자 (기본값: 공백)
            
        Returns:
            전체 텍스트 문자열
            
        Example:
            >>> ocr = EasyOCRReader()
            >>> text = ocr.extract_full_text('document.jpg', separator='\\n')
            >>> print(text)
        """
        texts = self.extract_text_only(image_path, min_confidence)
        return separator.join(texts)


if __name__ == "__main__":
    # 테스트 코드
    print("EasyOCR Reader Test")
    print("=" * 60)
    
    try:
        # OCR 초기화
        ocr = EasyOCRReader(languages=['ko', 'en'], gpu=True)
        print("[OK] EasyOCR initialized (GPU mode)")
        print(f"Languages: {ocr.languages}")
        print(f"GPU: {ocr.gpu}")
        
    except Exception as e:
        print(f"[ERROR] Initialization failed: {e}")
