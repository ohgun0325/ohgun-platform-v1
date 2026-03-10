"""Key-Value Extractor 테스트 및 사용 예제.

이 스크립트는 다음을 테스트합니다:
1. 다양한 표 레이아웃에서 Key-Value 추출
2. Structured PDF vs Scanned PDF 처리
3. 실제 문서에서 필드 추출
4. 성능 벤치마크
"""

import sys
import time
from pathlib import Path
from typing import Dict, Any

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))


def create_test_pdf_structured():
    """테스트용 Structured PDF 생성 (PyMuPDF 사용).
    
    다양한 레이아웃을 포함한 테스트 PDF를 생성합니다.
    """
    try:
        import fitz
    except ImportError:
        print("PyMuPDF가 필요합니다: pip install PyMuPDF")
        return None
    
    doc = fitz.open()
    
    # 페이지 1: 수평 레이아웃 (키: 왼쪽, 값: 오른쪽)
    page1 = doc.new_page(width=595, height=842)  # A4
    page1.insert_text((50, 100), "성명: 홍길동", fontsize=12)
    page1.insert_text((50, 130), "생년월일: 1990-01-01", fontsize=12)
    page1.insert_text((50, 160), "회사명: (주)테스트컴퍼니", fontsize=12)
    page1.insert_text((50, 190), "연락처: 010-1234-5678", fontsize=12)
    
    # 페이지 2: 수평 역방향 (값: 왼쪽, 키: 오른쪽)
    page2 = doc.new_page(width=595, height=842)
    page2.insert_text((250, 100), "성명", fontsize=12)
    page2.insert_text((50, 100), "김철수", fontsize=12)
    page2.insert_text((250, 130), "생년월일", fontsize=12)
    page2.insert_text((50, 130), "1985-05-15", fontsize=12)
    
    # 페이지 3: 수직 레이아웃 (키: 위, 값: 아래)
    page3 = doc.new_page(width=595, height=842)
    page3.insert_text((50, 100), "성명", fontsize=12)
    page3.insert_text((50, 120), "이영희", fontsize=12)
    page3.insert_text((50, 160), "생년월일", fontsize=12)
    page3.insert_text((50, 180), "1995-12-25", fontsize=12)
    
    # 저장
    test_pdf_path = project_root / "data" / "test_kv_extraction.pdf"
    test_pdf_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(test_pdf_path))
    doc.close()
    
    print(f"✓ 테스트 PDF 생성 완료: {test_pdf_path}")
    return test_pdf_path


def test_basic_extraction():
    """기본 추출 기능 테스트."""
    print("\n" + "="*60)
    print("테스트 1: 기본 Key-Value 추출")
    print("="*60)
    
    from app.domain.shared.pdf.key_value_extractor import extract_simple
    
    # 테스트 PDF 생성
    test_pdf = create_test_pdf_structured()
    if not test_pdf:
        return
    
    # 필드 정의
    keywords = {
        "name": ["성명", "이름"],
        "birth_date": ["생년월일", "출생일"],
        "company": ["회사명", "업체명"],
        "phone": ["연락처", "전화번호"],
    }
    
    # 페이지별 추출
    for page_num in [1, 2, 3]:
        print(f"\n--- 페이지 {page_num} ---")
        try:
            start = time.time()
            result = extract_simple(test_pdf, page_num, keywords)
            elapsed = time.time() - start
            
            print(f"추출 시간: {elapsed*1000:.1f}ms")
            for field, value in result.items():
                print(f"  {field}: {value}")
        except Exception as e:
            print(f"  오류: {e}")


def test_detailed_extraction():
    """상세 정보 포함 추출 테스트."""
    print("\n" + "="*60)
    print("테스트 2: 상세 추출 (bbox, confidence 포함)")
    print("="*60)
    
    from app.domain.shared.pdf.key_value_extractor import extract_with_details
    
    test_pdf = project_root / "data" / "test_kv_extraction.pdf"
    if not test_pdf.exists():
        print("테스트 PDF가 없습니다. test_basic_extraction()을 먼저 실행하세요.")
        return
    
    field_definitions = {
        "name": {
            "keywords": ["성명", "이름"],
            "post_process": lambda x: x.strip(),
        },
        "birth_date": {
            "keywords": ["생년월일"],
            "post_process": lambda x: x.replace(" ", ""),
        },
    }
    
    result = extract_with_details(test_pdf, 1, field_definitions)
    
    print(f"\n원본 단어 수: {len(result.get('raw_words', []))}")
    print("\n추출된 필드:")
    for field_name, field_data in result.get("fields", {}).items():
        print(f"\n  [{field_name}]")
        print(f"    키: {field_data['key']}")
        print(f"    값: {field_data['value']}")
        print(f"    방향: {field_data['direction']}")
        print(f"    거리: {field_data['distance']:.1f}px")
        print(f"    신뢰도: {field_data['confidence']:.3f}")
        print(f"    bbox: {field_data['bbox']}")


def test_unified_extractor():
    """통합 extractor 테스트 (자동 타입 감지)."""
    print("\n" + "="*60)
    print("테스트 3: 통합 Extractor (자동 PDF 타입 감지)")
    print("="*60)
    
    from app.domain.shared.pdf.unified_extractor import (
        UnifiedKeyValueExtractor,
        get_standard_field_definitions,
    )
    
    # OCR 리더 초기화 (옵션)
    ocr_reader = None
    try:
        from app.domain.shared.ocr.easyocr_reader import EasyOCRReader
        ocr_reader = EasyOCRReader(gpu=True, verbose=False)
        print("✓ EasyOCR 초기화 완료 (GPU 모드)")
    except Exception as e:
        print(f"⚠ EasyOCR 초기화 실패 (Structured PDF만 지원): {e}")
    
    # Extractor 생성
    extractor = UnifiedKeyValueExtractor(
        ocr_reader=ocr_reader,
        max_distance=300.0,
        same_line_tolerance=5.0,
    )
    
    # 필드 정의
    field_defs = get_standard_field_definitions()
    
    # 테스트 PDF
    test_pdf = project_root / "data" / "test_kv_extraction.pdf"
    if not test_pdf.exists():
        print("테스트 PDF가 없습니다.")
        return
    
    # 추출
    result = extractor.extract(test_pdf, 1, field_defs)
    
    print(f"\nPDF 타입: {result['pdf_type']}")
    print(f"추출 방법: {result['extraction_method']}")
    print(f"오류: {result['error']}")
    
    print("\n추출된 필드:")
    for field_name, data in result.get("fields", {}).items():
        print(f"  {field_name}: {data['value']} (신뢰도: {data['confidence']:.2f})")


def test_ocr_extraction():
    """OCR 기반 추출 테스트 (스캔 PDF 시뮬레이션)."""
    print("\n" + "="*60)
    print("테스트 4: OCR Key-Value 추출")
    print("="*60)
    
    try:
        from app.domain.shared.ocr.easyocr_reader import EasyOCRReader
        from app.domain.shared.pdf.key_value_extractor import extract_from_ocr_simple
    except ImportError as e:
        print(f"필요한 모듈을 import할 수 없습니다: {e}")
        return
    
    # OCR 초기화
    try:
        ocr_reader = EasyOCRReader(gpu=True, verbose=False)
        print("✓ EasyOCR 초기화 완료")
    except Exception as e:
        print(f"✗ EasyOCR 초기화 실패: {e}")
        return
    
    # 테스트 이미지 경로 (실제 스캔 문서 이미지)
    test_image_path = project_root / "data" / "ocr_data" / "test_form.jpg"
    
    if not test_image_path.exists():
        print(f"⚠ 테스트 이미지가 없습니다: {test_image_path}")
        print("  실제 스캔 문서 이미지를 준비하여 테스트하세요.")
        return
    
    # OCR 실행
    print(f"\nOCR 실행 중: {test_image_path.name}")
    start = time.time()
    ocr_results = ocr_reader.read_image(test_image_path)
    elapsed = time.time() - start
    
    print(f"OCR 완료: {len(ocr_results)}개 항목 인식 ({elapsed*1000:.1f}ms)")
    
    # Key-Value 추출
    keywords = {
        "name": ["성명", "이름"],
        "company": ["회사명", "업체명"],
        "phone": ["연락처", "전화번호"],
    }
    
    result = extract_from_ocr_simple(ocr_results, keywords, min_confidence=0.5)
    
    print("\n추출 결과:")
    for field, value in result.items():
        print(f"  {field}: {value}")


def test_batch_extraction():
    """배치 추출 테스트 (여러 페이지 동시 처리)."""
    print("\n" + "="*60)
    print("테스트 5: 배치 추출 (여러 페이지)")
    print("="*60)
    
    from app.domain.shared.pdf.unified_extractor import (
        UnifiedKeyValueExtractor,
        BatchExtractor,
        get_standard_field_definitions,
    )
    
    # Extractor 생성
    extractor = UnifiedKeyValueExtractor()
    batch = BatchExtractor(extractor)
    
    # 테스트 PDF
    test_pdf = project_root / "data" / "test_kv_extraction.pdf"
    if not test_pdf.exists():
        print("테스트 PDF가 없습니다.")
        return
    
    # 여러 페이지 동시 추출
    field_defs = get_standard_field_definitions()
    
    print("\n순차 처리...")
    start = time.time()
    results = batch.extract_multiple_pages(
        test_pdf,
        pages=[1, 2, 3],
        field_definitions=field_defs,
        parallel=False,
    )
    elapsed = time.time() - start
    
    print(f"완료: {elapsed*1000:.1f}ms")
    for page_num, result in results.items():
        print(f"\n페이지 {page_num}:")
        field_count = len(result.get("fields", {}))
        print(f"  추출된 필드: {field_count}개")
        if result.get("error"):
            print(f"  오류: {result['error']}")


def benchmark_extraction():
    """성능 벤치마크."""
    print("\n" + "="*60)
    print("벤치마크: 추출 성능 측정")
    print("="*60)
    
    from app.domain.shared.pdf.key_value_extractor import KeyValueExtractor
    
    test_pdf = project_root / "data" / "test_kv_extraction.pdf"
    if not test_pdf.exists():
        print("테스트 PDF가 없습니다.")
        return
    
    extractor = KeyValueExtractor()
    
    keywords = {
        "name": ["성명", "이름"],
        "birth_date": ["생년월일"],
        "company": ["회사명", "업체명"],
        "phone": ["연락처", "전화번호"],
    }
    
    # 10회 반복 측정
    times = []
    for _ in range(10):
        start = time.time()
        result = extractor.extract_from_pdf(test_pdf, 1, keywords)
        elapsed = time.time() - start
        times.append(elapsed * 1000)  # ms
    
    avg_time = sum(times) / len(times)
    min_time = min(times)
    max_time = max(times)
    
    print(f"\n추출 성능 (10회 평균):")
    print(f"  평균: {avg_time:.2f}ms")
    print(f"  최소: {min_time:.2f}ms")
    print(f"  최대: {max_time:.2f}ms")
    print(f"  처리량: ~{1000/avg_time:.1f} 페이지/초")


def example_usage_structured_pdf():
    """예제 1: Structured PDF에서 추출."""
    print("\n" + "="*60)
    print("예제 1: Structured PDF 추출")
    print("="*60)
    
    from app.domain.shared.pdf.unified_extractor import extract_from_any_pdf
    
    # 실제 PDF 경로 (사용자가 준비)
    pdf_path = input("\nPDF 파일 경로를 입력하세요 (엔터 = 테스트 PDF 사용): ").strip()
    
    if not pdf_path:
        pdf_path = project_root / "data" / "test_kv_extraction.pdf"
        if not pdf_path.exists():
            create_test_pdf_structured()
    
    page_num = 1
    
    # 필드 정의
    field_definitions = {
        "name": {
            "keywords": ["성명", "이름", "Name"],
            "post_process": lambda x: x.strip(),
        },
        "birth_date": {
            "keywords": ["생년월일", "출생일", "Birth Date"],
            "post_process": lambda x: x.replace(" ", "").replace(".", "-"),
        },
        "company": {
            "keywords": ["업체명", "회사명", "발행회사명"],
            "post_process": lambda x: x.strip(),
        },
        "phone": {
            "keywords": ["연락처", "전화번호", "Phone"],
            "post_process": lambda x: x.replace(" ", "").replace("-", ""),
        },
    }
    
    # 추출
    print(f"\n처리 중: {Path(pdf_path).name}, 페이지 {page_num}")
    result = extract_from_any_pdf(pdf_path, page_num, field_definitions)
    
    # 결과 출력
    print(f"\n[결과]")
    print(f"PDF 타입: {result['pdf_type']}")
    print(f"추출 방법: {result['extraction_method']}")
    
    if result.get("error"):
        print(f"오류: {result['error']}")
        return
    
    print(f"\n추출된 필드:")
    for field_name, data in result.get("fields", {}).items():
        print(f"  {field_name}:")
        print(f"    값: {data['value']}")
        print(f"    키: {data['key']}")
        print(f"    방향: {data['direction']}")
        print(f"    신뢰도: {data['confidence']:.3f}")


def example_usage_with_ocr():
    """예제 2: OCR 지원 (스캔 PDF 또는 폴백)."""
    print("\n" + "="*60)
    print("예제 2: OCR 지원 추출 (스캔 PDF)")
    print("="*60)
    
    try:
        from app.domain.shared.ocr.easyocr_reader import EasyOCRReader
        from app.domain.shared.pdf.unified_extractor import (
            create_production_extractor,
            get_standard_field_definitions,
        )
    except ImportError as e:
        print(f"필요한 모듈을 import할 수 없습니다: {e}")
        return
    
    # Production extractor 생성
    print("\nProduction extractor 초기화 중...")
    extractor = create_production_extractor(enable_ocr=True, gpu=True)
    
    # 필드 정의
    field_defs = get_standard_field_definitions()
    
    # PDF 경로
    pdf_path = input("\nPDF 파일 경로를 입력하세요: ").strip()
    if not pdf_path or not Path(pdf_path).exists():
        print("유효한 PDF 경로를 입력하세요.")
        return
    
    page_num = int(input("페이지 번호 (1-based): ").strip() or "1")
    
    # 추출
    print(f"\n처리 중...")
    start = time.time()
    result = extractor.extract(pdf_path, page_num, field_defs)
    elapsed = time.time() - start
    
    # 결과
    print(f"\n[결과] ({elapsed*1000:.1f}ms)")
    print(f"PDF 타입: {result['pdf_type']}")
    print(f"추출 방법: {result['extraction_method']}")
    
    if result.get("error"):
        print(f"오류: {result['error']}")
        return
    
    print(f"\n추출된 필드 ({len(result['fields'])}개):")
    for field_name, data in result.get("fields", {}).items():
        print(f"  {field_name}: {data['value']} (conf: {data['confidence']:.2f})")


def example_koica_proposal():
    """예제 3: KOICA 제안서 필드 추출."""
    print("\n" + "="*60)
    print("예제 3: KOICA 제안서 필드 추출")
    print("="*60)
    
    from app.domain.shared.pdf.unified_extractor import (
        extract_from_any_pdf,
        get_koica_proposal_field_definitions,
    )
    
    # 제안서 PDF 경로
    pdf_path = input("\nKOICA 제안서 PDF 경로를 입력하세요: ").strip()
    if not pdf_path or not Path(pdf_path).exists():
        print("유효한 PDF 경로를 입력하세요.")
        return
    
    page_num = 1  # 보통 첫 페이지에 메타데이터
    
    # KOICA 전용 필드 정의
    field_defs = get_koica_proposal_field_definitions()
    
    # OCR 리더 (옵션)
    ocr_reader = None
    try:
        from app.domain.shared.ocr.easyocr_reader import EasyOCRReader
        ocr_reader = EasyOCRReader(gpu=True, verbose=False)
    except Exception:
        pass
    
    # 추출
    print(f"\n처리 중: {Path(pdf_path).name}")
    result = extract_from_any_pdf(pdf_path, page_num, field_defs, ocr_reader)
    
    # 결과
    print(f"\n[KOICA 제안서 정보]")
    print(f"PDF 타입: {result['pdf_type']}")
    
    if result.get("error"):
        print(f"오류: {result['error']}")
        return
    
    fields = result.get("fields", {})
    
    # 주요 필드 출력
    if "proposal_title" in fields:
        print(f"\n사업명: {fields['proposal_title']['value']}")
    if "proposer_name" in fields:
        print(f"제안기관: {fields['proposer_name']['value']}")
    if "target_country" in fields:
        print(f"대상국가: {fields['target_country']['value']}")
    if "total_budget" in fields:
        print(f"총 사업비: {fields['total_budget']['value']}")
    if "project_period" in fields:
        print(f"사업기간: {fields['project_period']['value']}")
    
    # 전체 필드 출력
    print(f"\n전체 추출 필드 ({len(fields)}개):")
    for field_name, data in fields.items():
        print(f"  {field_name}: {data['value']}")


def show_best_practices():
    """Production 환경 Best Practices 가이드."""
    print("\n" + "="*60)
    print("Production 환경 Best Practices")
    print("="*60)
    
    practices = """
1. **Extractor 재사용**
   - UnifiedKeyValueExtractor를 앱 시작 시 한 번 생성하여 재사용
   - OCR 모델 초기화 비용이 크므로 (5~10초) 매 요청마다 생성하지 말 것
   
   예시:
   ```python
   # 앱 시작 시
   global_extractor = create_production_extractor(enable_ocr=True, gpu=True)
   
   # 요청마다
   def handle_pdf_request(pdf_path, page_num):
       return global_extractor.extract(pdf_path, page_num, field_defs)
   ```

2. **GPU 활성화**
   - EasyOCR은 GPU에서 10배 이상 빠름 (CPU: ~5초/페이지, GPU: ~0.5초/페이지)
   - RTX 3070 Ti 이상 권장
   - CUDA 설치 필수: https://developer.nvidia.com/cuda-downloads

3. **필드 정의 최적화**
   - 키워드는 가장 일반적인 것부터 나열 (빈도 높은 순)
   - 띄어쓰기 변형 포함 ("생년월일", "생 년 월 일")
   - 동의어/영문 포함 ("성명", "이름", "Name")
   
   예시:
   ```python
   field_defs = {
       "name": {
           "keywords": ["성명", "이름", "담당자명", "Name"],  # 일반적 → 구체적
           "post_process": lambda x: x.strip(),
       },
   }
   ```

4. **오류 처리**
   - auto_fallback=True로 설정하여 PyMuPDF 실패 시 자동 OCR
   - result["error"]를 항상 체크
   - confidence가 낮은 결과는 사람이 검토
   
   예시:
   ```python
   result = extractor.extract(pdf_path, page_num, field_defs, auto_fallback=True)
   
   if result["error"]:
       logger.error(f"추출 실패: {result['error']}")
       return None
   
   for field_name, data in result["fields"].items():
       if data["confidence"] < 0.7:
           logger.warning(f"{field_name} 신뢰도 낮음: {data['confidence']}")
   ```

5. **성능 최적화**
   
   a. PDF 타입 미리 알고 있는 경우:
   ```python
   # Structured PDF만 처리
   from app.domain.shared.pdf.key_value_extractor import extract_with_details
   result = extract_with_details(pdf_path, page_num, field_defs)
   ```
   
   b. 여러 페이지 처리:
   ```python
   # 배치 처리 (순차)
   batch = BatchExtractor(extractor)
   results = batch.extract_multiple_pages(pdf_path, [1,2,3,4,5], field_defs)
   ```
   
   c. OCR 최소화:
   ```python
   # 텍스트 임계값 낮춤 (더 많은 PDF를 structured로 처리)
   extractor = UnifiedKeyValueExtractor(
       ocr_reader=ocr,
       text_threshold=30,  # 기본값: 50
   )
   ```

6. **False Positive 줄이기**
   
   a. 최대 거리 조정:
   ```python
   # 가까운 값만 매칭 (표가 촘촘한 경우)
   extractor = UnifiedKeyValueExtractor(max_distance=150.0)
   ```
   
   b. post_process로 검증:
   ```python
   def validate_phone(text: str) -> str:
       # 전화번호 형식 검증
       import re
       text = text.replace(" ", "").replace("-", "")
       if re.match(r'^0\d{9,10}$', text):
           return text
       raise ValueError("Invalid phone format")
   
   field_defs = {
       "phone": {
           "keywords": ["연락처"],
           "post_process": validate_phone,
       }
   }
   ```
   
   c. 신뢰도 필터링:
   ```python
   valid_fields = {
       k: v for k, v in result["fields"].items()
       if v["confidence"] >= 0.7
   }
   ```

7. **로깅 및 모니터링**
   ```python
   import logging
   
   logging.basicConfig(
       level=logging.INFO,
       format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
   )
   
   logger = logging.getLogger(__name__)
   ```

8. **에러 핸들링 패턴**
   ```python
   try:
       result = extractor.extract(pdf_path, page_num, field_defs)
       
       if result["error"]:
           # 사용자에게 에러 알림
           return {"status": "error", "message": result["error"]}
       
       # 신뢰도 체크
       low_confidence_fields = [
           k for k, v in result["fields"].items()
           if v["confidence"] < 0.7
       ]
       
       if low_confidence_fields:
           # 사람 검토 필요
           return {
               "status": "review_required",
               "fields": result["fields"],
               "review_fields": low_confidence_fields,
           }
       
       # 성공
       return {
           "status": "success",
           "fields": {k: v["value"] for k, v in result["fields"].items()},
       }
   
   except Exception as e:
       logger.exception("예상치 못한 오류")
       return {"status": "error", "message": str(e)}
   ```

9. **메모리 관리**
   - 대용량 PDF 처리 시 페이지별 처리 (전체 로드 금지)
   - OCR 이미지는 처리 후 즉시 삭제
   - 배치 처리 시 청크 단위로 나눔 (한 번에 너무 많은 페이지 처리 금지)

10. **다양한 레이아웃 대응**
    
    a. 같은 줄 허용 오차 조정:
    ```python
    # 행 간격이 좁은 표
    extractor = UnifiedKeyValueExtractor(same_line_tolerance=3.0)
    
    # 행 간격이 넓은 표
    extractor = UnifiedKeyValueExtractor(same_line_tolerance=10.0)
    ```
    
    b. 방향별 가중치 커스터마이징:
    ```python
    from app.domain.shared.pdf.key_value_extractor import Direction
    
    # 수직 레이아웃이 많은 경우
    custom_weights = {
        Direction.SAME_LINE: 10.0,
        Direction.RIGHT: 3.0,
        Direction.BELOW: 8.0,  # 아래를 더 선호
        Direction.LEFT: 1.0,
        Direction.ABOVE: 0.5,
    }
    
    extractor = KeyValueExtractor(direction_weights=custom_weights)
    ```
    
    c. 키워드 변형 추가:
    ```python
    # 띄어쓰기 변형, 오타 대응
    keywords = [
        "성명", "성 명",  # 띄어쓰기
        "이름", "이 름",
        "Name", "NAME",  # 대소문자
        "담당자명",      # 복합어
    ]
    ```
"""
    print(practices)


def interactive_demo():
    """인터랙티브 데모."""
    print("\n" + "="*60)
    print("Key-Value Extractor 인터랙티브 데모")
    print("="*60)
    
    print("\n메뉴:")
    print("1. 테스트 PDF 생성 및 기본 추출")
    print("2. 상세 추출 (bbox, confidence 포함)")
    print("3. 통합 Extractor (자동 타입 감지)")
    print("4. OCR 추출 테스트")
    print("5. 배치 추출 (여러 페이지)")
    print("6. 성능 벤치마크")
    print("7. Structured PDF 예제")
    print("8. OCR 지원 예제")
    print("9. KOICA 제안서 예제")
    print("10. Best Practices 가이드")
    print("0. 종료")
    
    choice = input("\n선택하세요 (0-10): ").strip()
    
    if choice == "1":
        test_basic_extraction()
    elif choice == "2":
        test_detailed_extraction()
    elif choice == "3":
        test_unified_extractor()
    elif choice == "4":
        test_ocr_extraction()
    elif choice == "5":
        test_batch_extraction()
    elif choice == "6":
        benchmark_extraction()
    elif choice == "7":
        example_usage_structured_pdf()
    elif choice == "8":
        example_usage_with_ocr()
    elif choice == "9":
        example_koica_proposal()
    elif choice == "10":
        show_best_practices()
    elif choice == "0":
        print("\n종료합니다.")
        return
    else:
        print("\n잘못된 선택입니다.")


if __name__ == "__main__":
    print("="*60)
    print("PDF Key-Value Extractor 테스트 스위트")
    print("="*60)
    print("\nPyMuPDF + EasyOCR 기반 production-level 추출 시스템")
    print("다양한 표 레이아웃 지원 (수평, 수직, 혼합)")
    
    # 대화형 모드
    interactive_demo()
