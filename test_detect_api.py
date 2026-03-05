"""인감도장 검출 API 테스트 스크립트"""
import requests

# 테스트할 PDF 파일
pdf_path = "data/koica_detect_row_pdfs/키르기스스탄 PMC 부분_(직인 제출서류).pdf"

# API 엔드포인트 (FastAPI 백엔드 포트: 8000)
url = "http://localhost:8000/api/v1/detect"

# PDF 파일 전송
with open(pdf_path, "rb") as f:
    files = {"file": (pdf_path.split("/")[-1], f, "application/pdf")}
    response = requests.post(url, files=files)

print("=" * 60)
print("Status Code:", response.status_code)
print("=" * 60)

if response.status_code == 200:
    result = response.json()
    print("\n[OK] 검출 성공")
    print(f"총 페이지: {result['num_pages']}")
    print(f"인감도장 검출: {'있음' if result['summary']['has_stamp_any'] else '없음'}")
    print(f"서명 검출: {'있음' if result['summary']['has_signature_any'] else '없음'}")
    print(f"인감도장 페이지: {result['summary']['stamp_pages']}")
    print(f"서명 페이지: {result['summary']['signature_pages']}")

    print("\n📄 페이지별 검출 상세:")
    for page in result['pages'][:3]:  # 처음 3페이지만
        print(f"  페이지 {page['page_index']}: 검출 {len(page['detections'])}개")
        for det in page['detections'][:3]:  # 각 페이지에서 최대 3개만
            print(f"    - {det['cls']}: {det['conf']:.2%}")
else:
    print(f"\n❌ 오류 발생")
    print("Response:", response.text)

print("=" * 60)
