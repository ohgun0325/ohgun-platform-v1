"""
OCR 전처리 유틸리티
LLM 호출 전에 수행하는 정규식 기반 정규화
"""

import re
from typing import Dict, List, Tuple


def normalize_phone_number(text: str) -> str:
    """전화번호 형식 정규화 (하이픈 추가)
    
    예: 01012345678 → 010-1234-5678
        02-1234-5678 → 02-1234-5678 (유지)
    """
    # 하이픈 없는 휴대폰 번호
    text = re.sub(r'(\d{3})(\d{4})(\d{4})(?!\d)', r'\1-\2-\3', text)
    # 하이픈 없는 지역번호 (02, 031 등)
    text = re.sub(r'(\d{2,3})(\d{3,4})(\d{4})(?!\d)', r'\1-\2-\3', text)
    return text


def normalize_business_number(text: str) -> str:
    """사업자번호 형식 정규화
    
    예: 1234567890 → 123-45-67890
    """
    text = re.sub(r'(\d{3})(\d{2})(\d{5})(?!\d)', r'\1-\2-\3', text)
    return text


def normalize_date(text: str) -> str:
    """날짜 형식 통일 (YYYY.MM.DD)
    
    예: 2025년 01월 02일 → 2025.01.02
        2025-01-02 → 2025.01.02
    """
    # YYYY년 MM월 DD일 형식
    text = re.sub(
        r'(\d{4})\s*년\s*(\d{1,2})\s*월\s*(\d{1,2})\s*일?',
        lambda m: f"{m.group(1)}.{m.group(2).zfill(2)}.{m.group(3).zfill(2)}",
        text
    )
    # YYYY-MM-DD 또는 YYYY/MM/DD 형식
    text = re.sub(
        r'(\d{4})[-/](\d{1,2})[-/](\d{1,2})',
        lambda m: f"{m.group(1)}.{m.group(2).zfill(2)}.{m.group(3).zfill(2)}",
        text
    )
    return text


def normalize_spacing(text: str) -> str:
    """연속 공백을 하나로 정리"""
    return re.sub(r'\s+', ' ', text).strip()


def extract_phone_numbers(text: str) -> List[str]:
    """전화번호 패턴 추출"""
    patterns = [
        r'\d{3}-\d{4}-\d{4}',  # 010-1234-5678
        r'\d{2,3}-\d{3,4}-\d{4}',  # 02-123-4567
        r'\d{10,11}',  # 하이픈 없는 번호
    ]
    results = []
    for pattern in patterns:
        results.extend(re.findall(pattern, text))
    return list(set(results))


def extract_business_numbers(text: str) -> List[str]:
    """사업자번호 패턴 추출"""
    patterns = [
        r'\d{3}-\d{2}-\d{5}',  # 123-45-67890
        r'\d{10}',  # 하이픈 없는 번호
    ]
    results = []
    for pattern in patterns:
        results.extend(re.findall(pattern, text))
    return list(set(results))


def extract_dates(text: str) -> List[str]:
    """날짜 패턴 추출"""
    patterns = [
        r'\d{4}\.\d{2}\.\d{2}',  # 2025.01.02
        r'\d{4}년\s*\d{1,2}월\s*\d{1,2}일',  # 2025년 1월 2일
        r'\d{4}[-/]\d{1,2}[-/]\d{1,2}',  # 2025-01-02
    ]
    results = []
    for pattern in patterns:
        results.extend(re.findall(pattern, text))
    return list(set(results))


def extract_field_context(
    text: str,
    label: str,
    window_size: int = 100
) -> str:
    """라벨 주변 텍스트 추출
    
    Args:
        text: 전체 OCR 텍스트
        label: 찾을 라벨 (예: "성명", "회사명")
        window_size: 라벨 전후로 추출할 문자 수
        
    Returns:
        라벨 주변 텍스트 (라벨이 없으면 빈 문자열)
    """
    idx = text.find(label)
    if idx == -1:
        return ""
    
    start = max(0, idx - window_size // 2)
    end = min(len(text), idx + len(label) + window_size // 2)
    return text[start:end].strip()


def extract_all_field_contexts(
    text: str,
    field_labels: Dict[str, List[str]],
    window_size: int = 100
) -> Dict[str, str]:
    """모든 필드의 라벨 주변 텍스트 추출
    
    Args:
        text: 전체 OCR 텍스트
        field_labels: 필드명 → 라벨 리스트 매핑
            예: {"담당자이름": ["성명", "담당자명"], "회사명": ["회사명", "발행회사명"]}
        window_size: 라벨 전후로 추출할 문자 수
        
    Returns:
        필드명 → 주변 텍스트 매핑
    """
    contexts = {}
    for field_name, labels in field_labels.items():
        for label in labels:
            context = extract_field_context(text, label, window_size)
            if context:
                contexts[field_name] = context
                break
    return contexts


def preprocess_ocr_text(text: str) -> Tuple[str, Dict[str, List[str]]]:
    """OCR 텍스트 전처리 (LLM 호출 전)
    
    Returns:
        (정규화된 텍스트, 추출된 패턴들)
    """
    # 1. 공백 정리
    text = normalize_spacing(text)
    
    # 2. 형식 정규화
    text = normalize_phone_number(text)
    text = normalize_business_number(text)
    text = normalize_date(text)
    
    # 3. 패턴 추출
    patterns = {
        'phone_numbers': extract_phone_numbers(text),
        'business_numbers': extract_business_numbers(text),
        'dates': extract_dates(text),
    }
    
    return text, patterns
