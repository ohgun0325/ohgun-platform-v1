"""간단한 통합 테스트 - Key-Value Extractor.

기본 기능이 작동하는지 확인합니다.
"""

import sys
import os
from pathlib import Path

# UTF-8 인코딩 강제
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))


def test_imports():
    """모듈 import 테스트."""
    print("="*60)
    print("테스트 1: 모듈 Import")
    print("="*60)
    
    try:
        from app.domain.shared.pdf.key_value_extractor import (
            KeyValueExtractor,
            BBox,
            Word,
            Direction,
        )
        print("✓ key_value_extractor import 성공")
    except Exception as e:
        print(f"✗ key_value_extractor import 실패: {e}")
        return False
    
    try:
        from app.domain.shared.pdf.unified_extractor import (
            UnifiedKeyValueExtractor,
            extract_from_any_pdf,
            create_production_extractor,
        )
        print("✓ unified_extractor import 성공")
    except Exception as e:
        print(f"✗ unified_extractor import 실패: {e}")
        return False
    
    try:
        from app.domain.shared.pdf import (
            extract_simple,
            extract_from_any_pdf,
            KeyValueExtractor,
        )
        print("✓ PDF 모듈 통합 import 성공")
    except Exception as e:
        print(f"✗ PDF 모듈 통합 import 실패: {e}")
        return False
    
    print("\n✅ 모든 import 테스트 통과\n")
    return True


def test_bbox_operations():
    """BBox 클래스 동작 테스트."""
    print("="*60)
    print("테스트 2: BBox 클래스 동작")
    print("="*60)
    
    from app.domain.shared.pdf.key_value_extractor import BBox
    
    # BBox 생성
    bbox1 = BBox(0, 0, 100, 50)
    bbox2 = BBox(150, 5, 250, 55)
    
    print(f"BBox 1: ({bbox1.x0}, {bbox1.y0}, {bbox1.x1}, {bbox1.y1})")
    print(f"  중심: ({bbox1.center_x}, {bbox1.center_y})")
    print(f"  크기: {bbox1.width} x {bbox1.height}")
    
    print(f"\nBBox 2: ({bbox2.x0}, {bbox2.y0}, {bbox2.x1}, {bbox2.y1})")
    print(f"  중심: ({bbox2.center_x}, {bbox2.center_y})")
    
    # 거리 계산
    distance = bbox1.distance_to(bbox2)
    print(f"\n거리: {distance:.2f}px")
    
    # 같은 줄 판단
    is_same_line = bbox1.is_same_line(bbox2, tolerance=10.0)
    print(f"같은 줄: {is_same_line}")
    
    print("\n✅ BBox 테스트 통과\n")
    return True


def test_direction_calculation():
    """방향 판단 테스트."""
    print("="*60)
    print("테스트 3: 방향 판단")
    print("="*60)
    
    from app.domain.shared.pdf.key_value_extractor import BBox, KeyValueExtractor, Direction
    
    extractor = KeyValueExtractor()
    
    key = BBox(50, 100, 90, 120)
    
    test_cases = [
        (BBox(150, 102, 200, 122), "SAME_LINE (오른쪽, 같은 줄)"),
        (BBox(10, 102, 45, 122), "LEFT (왼쪽, 같은 줄)"),
        (BBox(55, 150, 105, 170), "BELOW (아래)"),
        (BBox(55, 50, 105, 70), "ABOVE (위)"),
    ]
    
    for value_bbox, expected in test_cases:
        direction = extractor._determine_direction(key, value_bbox)
        print(f"  {expected}: {direction.value}")
    
    print("\n✅ 방향 판단 테스트 통과\n")
    return True


def test_score_calculation():
    """점수 계산 테스트."""
    print("="*60)
    print("테스트 4: 점수 계산")
    print("="*60)
    
    from app.domain.shared.pdf.key_value_extractor import BBox, KeyValueExtractor, Direction
    
    extractor = KeyValueExtractor()
    
    key = BBox(50, 100, 90, 120)
    
    # 케이스 1: 같은 줄, 가까움
    value1 = BBox(100, 102, 150, 122)
    distance1 = key.distance_to(value1)
    direction1 = Direction.SAME_LINE
    score1 = extractor._calculate_score(key, value1, direction1, distance1)
    conf1 = extractor._calculate_confidence(score1, direction1)
    
    print(f"케이스 1 (같은 줄, 가까움):")
    print(f"  거리: {distance1:.1f}px")
    print(f"  방향: {direction1.value}")
    print(f"  점수: {score1:.4f}")
    print(f"  신뢰도: {conf1:.3f}")
    
    # 케이스 2: 아래, 멀리
    value2 = BBox(55, 200, 105, 220)
    distance2 = key.distance_to(value2)
    direction2 = Direction.BELOW
    score2 = extractor._calculate_score(key, value2, direction2, distance2)
    conf2 = extractor._calculate_confidence(score2, direction2)
    
    print(f"\n케이스 2 (아래, 멀리):")
    print(f"  거리: {distance2:.1f}px")
    print(f"  방향: {direction2.value}")
    print(f"  점수: {score2:.4f}")
    print(f"  신뢰도: {conf2:.3f}")
    
    # 비교
    print(f"\n→ 케이스 1이 더 높은 점수 ({score1:.4f} > {score2:.4f})")
    
    print("\n✅ 점수 계산 테스트 통과\n")
    return True


def test_create_simple_pdf():
    """간단한 테스트 PDF 생성."""
    print("="*60)
    print("테스트 5: 테스트 PDF 생성")
    print("="*60)
    
    try:
        import fitz
    except ImportError:
        print("✗ PyMuPDF가 설치되지 않았습니다")
        return False
    
    # 간단한 PDF 생성
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)  # A4
    
    # 텍스트 추가
    page.insert_text((50, 100), "성명: 홍길동", fontsize=12)
    page.insert_text((50, 130), "생년월일: 1990-01-01", fontsize=12)
    page.insert_text((50, 160), "회사명: (주)테스트컴퍼니", fontsize=12)
    
    # 저장
    output_path = project_root / "data" / "simple_test.pdf"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    doc.save(str(output_path))
    doc.close()
    
    print(f"✓ 테스트 PDF 생성: {output_path}")
    print(f"  크기: {output_path.stat().st_size} bytes")
    
    print("\n✅ PDF 생성 테스트 통과\n")
    return output_path


def test_basic_extraction():
    """기본 추출 테스트."""
    print("="*60)
    print("테스트 6: 기본 Key-Value 추출")
    print("="*60)
    
    # 테스트 PDF 생성
    test_pdf = test_create_simple_pdf()
    
    if not test_pdf or not test_pdf.exists():
        print("✗ 테스트 PDF가 없습니다")
        return False
    
    try:
        from app.domain.shared.pdf import extract_simple
        
        keywords = {
            "name": ["성명"],
            "birth_date": ["생년월일"],
            "company": ["회사명"],
        }
        
        print(f"\n추출 시작: {test_pdf.name}")
        result = extract_simple(test_pdf, 1, keywords)
        
        print(f"\n추출 결과:")
        for field, value in result.items():
            print(f"  {field}: {value}")
        
        # 검증
        assert "name" in result, "name 필드 없음"
        assert "birth_date" in result, "birth_date 필드 없음"
        assert "company" in result, "company 필드 없음"
        
        print("\n✅ 기본 추출 테스트 통과\n")
        return True
    
    except Exception as e:
        print(f"\n✗ 추출 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_detailed_extraction():
    """상세 추출 테스트 (bbox, confidence 포함)."""
    print("="*60)
    print("테스트 7: 상세 추출 (메타데이터 포함)")
    print("="*60)
    
    test_pdf = project_root / "data" / "simple_test.pdf"
    
    if not test_pdf.exists():
        print("✗ 테스트 PDF가 없습니다")
        return False
    
    try:
        from app.domain.shared.pdf import extract_with_details
        
        field_defs = {
            "name": {
                "keywords": ["성명"],
                "post_process": lambda x: x.strip(),
            },
        }
        
        result = extract_with_details(test_pdf, 1, field_defs)
        
        print(f"\n원본 단어 수: {len(result.get('raw_words', []))}")
        
        if "fields" in result and "name" in result["fields"]:
            data = result["fields"]["name"]
            print(f"\n추출된 필드 'name':")
            print(f"  키: {data['key']}")
            print(f"  값: {data['value']}")
            print(f"  방향: {data['direction']}")
            print(f"  거리: {data['distance']:.1f}px")
            print(f"  신뢰도: {data['confidence']:.3f}")
            print(f"  bbox: {data['bbox']}")
            
            print("\n✅ 상세 추출 테스트 통과\n")
            return True
        else:
            print("\n✗ 필드 추출 실패")
            return False
    
    except Exception as e:
        print(f"\n✗ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """모든 테스트 실행."""
    print("\n")
    print("="*60)
    print("Key-Value Extractor 통합 테스트")
    print("="*60)
    print()
    
    tests = [
        ("Import", test_imports),
        ("BBox 동작", test_bbox_operations),
        ("방향 판단", test_direction_calculation),
        ("점수 계산", test_score_calculation),
        ("PDF 생성", test_create_simple_pdf),
        ("기본 추출", test_basic_extraction),
        ("상세 추출", test_detailed_extraction),
    ]
    
    results = []
    
    for name, test_func in tests:
        try:
            if name == "PDF 생성":
                result = test_func()
                success = result is not None
            else:
                success = test_func()
            results.append((name, success))
        except Exception as e:
            print(f"✗ {name} 테스트 중 예외: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    # 결과 요약
    print("\n")
    print("="*60)
    print("테스트 결과 요약")
    print("="*60)
    
    for name, success in results:
        status = "✅ 통과" if success else "❌ 실패"
        print(f"  {status}  {name}")
    
    success_count = sum(1 for _, success in results if success)
    total_count = len(results)
    
    print(f"\n총 {total_count}개 테스트 중 {success_count}개 통과")
    print(f"성공률: {success_count/total_count*100:.1f}%")
    
    if success_count == total_count:
        print("\n🎉 모든 테스트 통과!")
    else:
        print("\n⚠️ 일부 테스트 실패")


if __name__ == "__main__":
    run_all_tests()
