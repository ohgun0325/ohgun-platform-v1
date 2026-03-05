# Key-Value Extractor Quick Start

5분 안에 시작하는 PDF Key-Value 추출 시스템

---

## 🚀 빠른 시작

### 1단계: 설치

```bash
pip install PyMuPDF easyocr pillow numpy torch
```

GPU 지원 (권장):
```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
```

### 2단계: 기본 사용

```python
from app.domain.shared.pdf.unified_extractor import extract_simple_dict

# PDF에서 필드 추출
result = extract_simple_dict(
    pdf_path="my_form.pdf",
    page_num=1,
    keywords={
        "name": ["성명", "이름"],
        "company": ["회사명", "업체명"],
    }
)

print(result["name"])     # "홍길동"
print(result["company"])  # "(주)테스트컴퍼니"
```

### 3단계: OCR 지원 (스캔 PDF)

```python
from app.domain.shared.ocr.easyocr_reader import EasyOCRReader
from app.domain.shared.pdf.unified_extractor import extract_from_any_pdf

# OCR 초기화 (앱 시작 시 한 번만)
ocr = EasyOCRReader(gpu=True)

# 필드 정의
fields = {
    "name": {"keywords": ["성명", "이름"]},
    "birth_date": {"keywords": ["생년월일"]},
}

# 추출 (자동 타입 감지)
result = extract_from_any_pdf("scanned.pdf", 1, fields, ocr)

print(f"PDF 타입: {result['pdf_type']}")  # "structured" or "scanned"
for field_name, data in result["fields"].items():
    print(f"{field_name}: {data['value']} (신뢰도: {data['confidence']:.2f})")
```

---

## 📝 실전 예제

### 예제 1: 신분증/증명서 정보 추출

```python
from app.domain.shared.pdf.unified_extractor import extract_from_any_pdf

# 필드 정의
id_card_fields = {
    "name": {
        "keywords": ["성명", "이름", "Name"],
        "post_process": lambda x: x.strip(),
    },
    "birth_date": {
        "keywords": ["생년월일", "출생일", "Date of Birth"],
        "post_process": lambda x: x.replace(" ", "").replace(".", "-"),
    },
    "id_number": {
        "keywords": ["주민등록번호", "Resident Number"],
        "post_process": lambda x: x.replace(" ", "").replace("-", ""),
    },
    "address": {
        "keywords": ["주소", "Address"],
        "post_process": lambda x: x.strip(),
    },
    "issue_date": {
        "keywords": ["발급일", "Issue Date"],
        "post_process": lambda x: x.replace(" ", ""),
    },
}

# 추출
result = extract_from_any_pdf("id_card.pdf", 1, id_card_fields)

# 결과 처리
if result["error"]:
    print(f"오류: {result['error']}")
else:
    person_info = {
        field: data["value"]
        for field, data in result["fields"].items()
        if data["confidence"] >= 0.7  # 신뢰도 70% 이상만
    }
    print(person_info)
```

---

### 예제 2: 계약서 주요 정보 추출

```python
# 계약서 필드 정의
contract_fields = {
    "contract_number": {
        "keywords": ["계약번호", "Contract No", "문서번호"],
    },
    "party_a": {
        "keywords": ["갑", "발주자", "Party A"],
    },
    "party_b": {
        "keywords": ["을", "수주자", "Party B"],
    },
    "contract_date": {
        "keywords": ["계약일", "계약체결일", "Date"],
        "post_process": lambda x: x.replace(" ", ""),
    },
    "contract_amount": {
        "keywords": ["계약금액", "총액", "Amount"],
        "post_process": lambda x: x.replace(",", "").replace(" ", ""),
    },
    "payment_terms": {
        "keywords": ["지급조건", "Payment Terms"],
    },
}

result = extract_from_any_pdf("contract.pdf", 1, contract_fields)

# 계약 정보 검증
required = ["contract_number", "party_a", "party_b", "contract_amount"]
missing = [f for f in required if f not in result["fields"]]

if missing:
    print(f"⚠️ 필수 정보 누락: {missing}")
else:
    print("✓ 모든 필수 정보 추출 완료")
```

---

### 예제 3: 입찰 서류 자동 검증

```python
from app.domain.shared.pdf.unified_extractor import create_production_extractor

# Production extractor 생성 (앱 초기화 시)
extractor = create_production_extractor(enable_ocr=True, gpu=True)

def validate_bid_submission(pdf_path: str) -> Dict[str, Any]:
    """입찰 제출 서류 자동 검증."""
    
    # 필수 필드
    required_fields = {
        "company_name": {
            "keywords": ["업체명", "회사명", "상호"],
        },
        "business_number": {
            "keywords": ["사업자번호", "사업자등록번호"],
        },
        "representative": {
            "keywords": ["대표자", "대표이사", "대표자명"],
        },
        "phone": {
            "keywords": ["연락처", "전화번호"],
        },
        "email": {
            "keywords": ["이메일", "Email"],
        },
    }
    
    # 추출
    result = extractor.extract(pdf_path, 1, required_fields)
    
    if result["error"]:
        return {
            "valid": False,
            "error": result["error"],
        }
    
    # 필드 검증
    extracted = result["fields"]
    validation_result = {
        "valid": True,
        "fields": {},
        "issues": [],
    }
    
    for field_name, definition in required_fields.items():
        if field_name not in extracted:
            validation_result["valid"] = False
            validation_result["issues"].append(f"{field_name} 누락")
        else:
            data = extracted[field_name]
            validation_result["fields"][field_name] = data["value"]
            
            # 신뢰도 체크
            if data["confidence"] < 0.7:
                validation_result["issues"].append(
                    f"{field_name} 신뢰도 낮음 ({data['confidence']:.2f})"
                )
    
    return validation_result

# 사용
validation = validate_bid_submission("bidder_doc.pdf")

if validation["valid"]:
    print("✓ 서류 검증 통과")
    print(validation["fields"])
else:
    print("✗ 서류 검증 실패")
    print("문제 사항:")
    for issue in validation["issues"]:
        print(f"  - {issue}")
```

---

### 예제 4: 배치 처리 (여러 PDF)

```python
from pathlib import Path
from app.domain.shared.pdf.unified_extractor import create_production_extractor
import json

# 초기화
extractor = create_production_extractor(enable_ocr=True, gpu=True)

def process_pdf_folder(folder_path: str, output_json: str):
    """폴더 내 모든 PDF를 처리하여 JSON으로 저장."""
    
    folder = Path(folder_path)
    pdf_files = list(folder.glob("*.pdf"))
    
    print(f"처리할 PDF: {len(pdf_files)}개")
    
    # 필드 정의
    from app.domain.shared.pdf.unified_extractor import get_standard_field_definitions
    field_defs = get_standard_field_definitions()
    
    # 결과 수집
    results = {}
    
    for idx, pdf_path in enumerate(pdf_files, 1):
        print(f"[{idx}/{len(pdf_files)}] 처리 중: {pdf_path.name}")
        
        try:
            result = extractor.extract(pdf_path, 1, field_defs)
            
            results[pdf_path.name] = {
                "status": "success" if not result["error"] else "error",
                "pdf_type": result["pdf_type"],
                "fields": {
                    k: v["value"]
                    for k, v in result.get("fields", {}).items()
                },
                "error": result.get("error"),
            }
        
        except Exception as e:
            results[pdf_path.name] = {
                "status": "error",
                "error": str(e),
            }
    
    # JSON 저장
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n✓ 완료: {output_json}")
    
    # 통계
    success = sum(1 for r in results.values() if r["status"] == "success")
    print(f"성공: {success}/{len(pdf_files)}")

# 사용
process_pdf_folder("./data/bid_documents/", "./output/extracted_fields.json")
```

---

### 예제 5: FastAPI 엔드포인트

```python
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Dict, List, Optional
import tempfile
from pathlib import Path

app = FastAPI(title="PDF Key-Value Extraction API")

# 글로벌 extractor (앱 시작 시 초기화)
from app.domain.shared.pdf.unified_extractor import create_production_extractor

extractor = create_production_extractor(enable_ocr=True, gpu=True)

class FieldRequest(BaseModel):
    keywords: List[str]

class ExtractionRequest(BaseModel):
    page_num: int = 1
    fields: Dict[str, FieldRequest]

@app.post("/extract/upload")
async def extract_from_upload(
    file: UploadFile = File(...),
    page_num: int = 1,
):
    """PDF 업로드 후 표준 필드 추출."""
    
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="PDF 파일만 지원됩니다")
    
    # 임시 파일 저장
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        contents = await file.read()
        tmp.write(contents)
        tmp_path = tmp.name
    
    try:
        # 표준 필드로 추출
        from app.domain.shared.pdf.unified_extractor import get_standard_field_definitions
        field_defs = get_standard_field_definitions()
        
        result = extractor.extract(tmp_path, page_num, field_defs)
        
        if result["error"]:
            raise HTTPException(status_code=500, detail=result["error"])
        
        return JSONResponse({
            "filename": file.filename,
            "pdf_type": result["pdf_type"],
            "extraction_method": result["extraction_method"],
            "fields": {
                k: {
                    "value": v["value"],
                    "confidence": v["confidence"],
                }
                for k, v in result["fields"].items()
            },
        })
    
    finally:
        Path(tmp_path).unlink(missing_ok=True)

@app.post("/extract/custom")
async def extract_custom_fields(
    file: UploadFile = File(...),
    request: ExtractionRequest = None,
):
    """커스텀 필드로 추출."""
    
    # (구현 생략)
    pass

# 실행
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

---

## ❓ FAQ

### Q1: 추출이 안 되는데 어떻게 디버깅하나요?

**A**: 단계별로 확인하세요.

```python
# 1. PDF에 텍스트가 있는지 확인
from app.domain.shared.pdf import extract_pdf_text
text = extract_pdf_text("problem.pdf")
print(text[:500])  # 처음 500자 확인

# 2. 키워드가 실제로 문서에 있는지 확인
if "성명" in text:
    print("키워드 '성명' 발견")
else:
    print("키워드가 문서에 없음 → 키워드 변경 필요")

# 3. 모든 단어와 bbox 확인
from app.domain.shared.pdf.key_value_extractor import KeyValueExtractor
extractor = KeyValueExtractor()
words = extractor._extract_words_from_pdf("problem.pdf", 1)

for word in words[:20]:  # 처음 20개 단어
    print(f"{word.text} at ({word.bbox.x0:.1f}, {word.bbox.y0:.1f})")

# 4. 상세 추출로 후보 확인
from app.domain.shared.pdf.key_value_extractor import extract_with_details
result = extract_with_details("problem.pdf", 1, field_defs)
print(result)  # 모든 정보 출력
```

---

### Q2: 잘못된 값이 추출됩니다.

**A**: 거리와 방향을 조정하세요.

```python
# 현재 설정 확인
extractor = KeyValueExtractor(
    max_distance=300.0,        # 기본값
    same_line_tolerance=5.0,   # 기본값
)

# 조정 옵션
# 옵션 1: 거리를 줄임 (가까운 것만 매칭)
extractor = KeyValueExtractor(max_distance=150.0)

# 옵션 2: 같은 줄 허용 오차 조정
extractor = KeyValueExtractor(same_line_tolerance=3.0)  # 더 엄격

# 옵션 3: 방향 가중치 조정
from app.domain.shared.pdf.key_value_extractor import Direction
custom_weights = {
    Direction.SAME_LINE: 10.0,
    Direction.RIGHT: 5.0,
    Direction.BELOW: 2.0,  # 아래 방향 약화
    Direction.LEFT: 1.0,
    Direction.ABOVE: 0.5,
}
extractor = KeyValueExtractor(direction_weights=custom_weights)
```

---

### Q3: OCR이 너무 느립니다.

**A**: GPU를 활성화하세요.

```python
# 1. CUDA 설치 확인
import torch
print(f"CUDA 사용 가능: {torch.cuda.is_available()}")
print(f"CUDA 버전: {torch.version.cuda}")

# 2. GPU 활성화
from app.domain.shared.ocr.easyocr_reader import EasyOCRReader
ocr = EasyOCRReader(gpu=True)  # gpu=True 필수

# 3. GPU 사용 확인
# nvidia-smi 명령어로 프로세스 확인

# 성능 비교:
# - CPU: ~4초/페이지
# - GPU: ~0.5초/페이지 (8배 빠름)
```

---

### Q4: 특정 필드만 추출하고 싶어요.

**A**: 필드 정의를 원하는 것만 포함하세요.

```python
# 성명과 회사명만 추출
minimal_fields = {
    "name": {"keywords": ["성명", "이름"]},
    "company": {"keywords": ["회사명", "업체명"]},
}

result = extract_from_any_pdf("doc.pdf", 1, minimal_fields)
```

---

### Q5: 동일한 키가 여러 번 나타나는 경우는?

**A**: `AdvancedExtractor`를 사용하세요.

```python
from app.domain.shared.pdf.unified_extractor import (
    UnifiedKeyValueExtractor,
    AdvancedExtractor,
)

base = UnifiedKeyValueExtractor()
advanced = AdvancedExtractor(base)

# 반복 필드 추출
team_members = advanced.extract_repeated_fields(
    pdf_path="team_roster.pdf",
    page_num=1,
    field_keywords=["담당자", "성명"],
)

print(team_members)  # ["홍길동", "김철수", "이영희"]
```

---

### Q6: 영문 문서도 지원하나요?

**A**: 네, 키워드에 영문을 추가하세요.

```python
# 다국어 필드 정의
multilingual_fields = {
    "name": {
        "keywords": ["성명", "이름", "Name", "Full Name"],
    },
    "company": {
        "keywords": ["회사명", "업체명", "Company", "Organization"],
    },
    "email": {
        "keywords": ["이메일", "Email", "E-mail"],
        "post_process": lambda x: x.strip().lower(),
    },
}

# EasyOCR도 다국어 지원
from app.domain.shared.ocr.easyocr_reader import EasyOCRReader
ocr = EasyOCRReader(languages=['ko', 'en', 'ja'])  # 한국어, 영어, 일본어
```

---

### Q7: 신뢰도가 낮은 결과는 어떻게 처리하나요?

**A**: 사람 검토 플래그를 추가하세요.

```python
result = extract_from_any_pdf(pdf_path, 1, field_defs)

CONFIDENCE_THRESHOLD = 0.7

validated_fields = {}
review_required = []

for field_name, data in result["fields"].items():
    if data["confidence"] >= CONFIDENCE_THRESHOLD:
        validated_fields[field_name] = data["value"]
    else:
        review_required.append({
            "field": field_name,
            "value": data["value"],
            "confidence": data["confidence"],
        })

# 결과
if review_required:
    print("⚠️ 검토 필요한 필드:")
    for item in review_required:
        print(f"  - {item['field']}: {item['value']} (신뢰도: {item['confidence']:.2f})")
else:
    print("✓ 모든 필드 신뢰도 충족")
```

---

### Q8: 여러 페이지에 정보가 분산되어 있습니다.

**A**: 배치 처리를 사용하세요.

```python
from app.domain.shared.pdf.unified_extractor import BatchExtractor

batch = BatchExtractor(extractor)

# 여러 페이지 처리
results = batch.extract_multiple_pages(
    pdf_path="multi_page_form.pdf",
    pages=[1, 2, 3],
    field_definitions=field_defs,
)

# 결과 병합
merged_fields = {}
for page_num, result in results.items():
    if not result["error"]:
        for field, data in result["fields"].items():
            # 첫 번째로 찾은 값 사용 (또는 신뢰도 높은 것)
            if field not in merged_fields:
                merged_fields[field] = data["value"]
            elif data["confidence"] > merged_fields.get(f"{field}_confidence", 0):
                merged_fields[field] = data["value"]

print(merged_fields)
```

---

### Q9: 표가 복잡해서 추출이 안 됩니다.

**A**: pdfplumber의 table extraction을 고려하세요.

```python
import pdfplumber

with pdfplumber.open("complex_table.pdf") as pdf:
    page = pdf.pages[0]
    tables = page.extract_tables()
    
    # 첫 번째 표
    if tables:
        table = tables[0]
        
        # 헤더 행
        headers = table[0]
        
        # 데이터 행
        for row in table[1:]:
            row_dict = dict(zip(headers, row))
            print(row_dict)

# pdfplumber + Key-Value extractor 결합 사용 권장
```

---

### Q10: 메모리가 부족합니다.

**A**: 페이지별 처리로 전환하세요.

```python
# ❌ 나쁜 예: 전체 PDF 로드
doc = fitz.open(large_pdf)
all_pages = list(range(len(doc)))
# ... 메모리 부족

# ✅ 좋은 예: 페이지별 처리
def process_large_pdf(pdf_path: str, field_defs: Dict):
    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    doc.close()
    
    results = {}
    
    for page_num in range(1, total_pages + 1):
        result = extractor.extract(pdf_path, page_num, field_defs)
        results[page_num] = result
        
        # 주기적으로 결과 저장 (중간 저장)
        if page_num % 10 == 0:
            save_intermediate_results(results)
    
    return results
```

---

## 🎯 Use Cases

### Use Case 1: KOICA 제안서 자동 분류

```python
from app.domain.shared.pdf.unified_extractor import (
    extract_from_any_pdf,
    get_koica_proposal_field_definitions,
)

def classify_koica_proposal(pdf_path: str) -> Dict[str, Any]:
    """KOICA 제안서에서 메타데이터 추출 및 분류."""
    
    field_defs = get_koica_proposal_field_definitions()
    result = extract_from_any_pdf(pdf_path, 1, field_defs)
    
    if result["error"]:
        return {"status": "error", "message": result["error"]}
    
    fields = result["fields"]
    
    # 사업 분류
    classification = {
        "proposal_info": {
            "title": fields.get("proposal_title", {}).get("value", "Unknown"),
            "organization": fields.get("proposer_name", {}).get("value", "Unknown"),
            "country": fields.get("target_country", {}).get("value", "Unknown"),
        },
        "project_info": {
            "budget": fields.get("total_budget", {}).get("value", "Unknown"),
            "period": fields.get("project_period", {}).get("value", "Unknown"),
        },
        "contact": {
            "person": fields.get("contact_person", {}).get("value", "Unknown"),
            "phone": fields.get("contact_phone", {}).get("value", "Unknown"),
        },
    }
    
    return classification

# 사용
info = classify_koica_proposal("proposal_001.pdf")
print(f"사업명: {info['proposal_info']['title']}")
print(f"대상국가: {info['proposal_info']['country']}")
```

---

### Use Case 2: 입찰 자격 사전 심사

```python
def pre_screen_bidder(pdf_path: str) -> Dict[str, Any]:
    """입찰 업체 자격 사전 심사."""
    
    # 필수 자격 요건
    qualification_fields = {
        "business_number": {
            "keywords": ["사업자번호", "사업자등록번호"],
        },
        "business_type": {
            "keywords": ["업태", "업종"],
        },
        "capital": {
            "keywords": ["자본금", "납입자본금"],
        },
        "established_date": {
            "keywords": ["설립일", "설립연월일"],
        },
    }
    
    result = extract_from_any_pdf(pdf_path, 1, qualification_fields)
    
    if result["error"]:
        return {"qualified": False, "reason": result["error"]}
    
    # 자격 검증
    fields = result["fields"]
    
    # 사업자번호 필수
    if "business_number" not in fields:
        return {"qualified": False, "reason": "사업자번호 없음"}
    
    # 자본금 확인 (예: 1억 이상)
    if "capital" in fields:
        capital_str = fields["capital"]["value"].replace(",", "").replace("원", "")
        try:
            capital = int(capital_str)
            if capital < 100000000:  # 1억
                return {"qualified": False, "reason": "자본금 부족"}
        except ValueError:
            pass  # 파싱 실패 시 넘어감
    
    return {
        "qualified": True,
        "company_info": {k: v["value"] for k, v in fields.items()},
    }

# 사용
screening = pre_screen_bidder("bidder_company_a.pdf")
if screening["qualified"]:
    print("✓ 사전 심사 통과")
else:
    print(f"✗ 사전 심사 탈락: {screening['reason']}")
```

---

### Use Case 3: 계약서 비교 분석

```python
def compare_contracts(pdf_paths: List[str]) -> Dict[str, Any]:
    """여러 계약서의 주요 조건 비교."""
    
    contract_fields = {
        "contract_amount": {
            "keywords": ["계약금액", "총액"],
            "post_process": lambda x: int(x.replace(",", "").replace("원", "")),
        },
        "contract_date": {
            "keywords": ["계약일", "계약체결일"],
        },
        "payment_terms": {
            "keywords": ["지급조건", "대금지급"],
        },
    }
    
    contracts = []
    
    for pdf_path in pdf_paths:
        result = extract_from_any_pdf(pdf_path, 1, contract_fields)
        
        if not result["error"]:
            contracts.append({
                "filename": Path(pdf_path).name,
                "amount": result["fields"].get("contract_amount", {}).get("value", 0),
                "date": result["fields"].get("contract_date", {}).get("value", "N/A"),
                "terms": result["fields"].get("payment_terms", {}).get("value", "N/A"),
            })
    
    # 금액 순 정렬
    contracts.sort(key=lambda x: x["amount"], reverse=True)
    
    return {
        "total_contracts": len(contracts),
        "total_amount": sum(c["amount"] for c in contracts),
        "highest": contracts[0] if contracts else None,
        "lowest": contracts[-1] if contracts else None,
        "contracts": contracts,
    }

# 사용
comparison = compare_contracts([
    "contract_a.pdf",
    "contract_b.pdf",
    "contract_c.pdf",
])

print(f"총 계약 건수: {comparison['total_contracts']}")
print(f"총 계약 금액: {comparison['total_amount']:,}원")
print(f"최대 계약: {comparison['highest']}")
```

---

## 🛠️ 커스터마이징 가이드

### 1. 커스텀 키워드 사전 만들기

```python
# custom_keywords.py

KOREAN_KEYWORDS = {
    "name": ["성명", "이름", "성 명", "담당자명"],
    "company": ["회사명", "업체명", "법인명", "상호"],
    "phone": ["연락처", "전화번호", "연 락 처", "전화"],
}

ENGLISH_KEYWORDS = {
    "name": ["Name", "Full Name", "Applicant Name"],
    "company": ["Company", "Organization", "Corporation"],
    "phone": ["Phone", "Tel", "Contact Number"],
}

def get_keywords(language: str = "ko") -> Dict[str, List[str]]:
    if language == "ko":
        return KOREAN_KEYWORDS
    elif language == "en":
        return ENGLISH_KEYWORDS
    else:
        # 다국어 혼합
        return {
            field: KOREAN_KEYWORDS.get(field, []) + ENGLISH_KEYWORDS.get(field, [])
            for field in set(KOREAN_KEYWORDS.keys()) | set(ENGLISH_KEYWORDS.keys())
        }
```

---

### 2. 커스텀 Post-processing

```python
import re

def process_phone_number(text: str) -> str:
    """전화번호 정규화."""
    # 숫자만 추출
    digits = re.sub(r'\D', '', text)
    
    # 010-XXXX-XXXX 형식으로 변환
    if len(digits) == 11 and digits.startswith('010'):
        return f"{digits[:3]}-{digits[3:7]}-{digits[7:]}"
    elif len(digits) == 10:
        return f"{digits[:3]}-{digits[3:6]}-{digits[6:]}"
    else:
        return text

def process_business_number(text: str) -> str:
    """사업자번호 정규화."""
    digits = re.sub(r'\D', '', text)
    
    # XXX-XX-XXXXX 형식
    if len(digits) == 10:
        return f"{digits[:3]}-{digits[3:5]}-{digits[5:]}"
    return text

def process_date(text: str) -> str:
    """날짜 정규화 (YYYY-MM-DD)."""
    # 구분자 통일
    text = text.replace(".", "-").replace("/", "-").replace(" ", "")
    
    # 검증
    if re.match(r'^\d{4}-\d{2}-\d{2}$', text):
        return text
    
    # YYYYMMDD → YYYY-MM-DD
    if re.match(r'^\d{8}$', text):
        return f"{text[:4]}-{text[4:6]}-{text[6:]}"
    
    return text

# 사용
field_definitions = {
    "phone": {
        "keywords": ["연락처", "전화번호"],
        "post_process": process_phone_number,
    },
    "business_number": {
        "keywords": ["사업자번호"],
        "post_process": process_business_number,
    },
    "date": {
        "keywords": ["작성일", "발행일"],
        "post_process": process_date,
    },
}
```

---

### 3. 커스텀 Validator

```python
from typing import Optional

class FieldValidator:
    """필드 검증기."""
    
    @staticmethod
    def validate_phone(value: str) -> Optional[str]:
        """전화번호 형식 검증."""
        digits = re.sub(r'\D', '', value)
        if len(digits) in [10, 11] and digits[0] == '0':
            return None  # 유효
        return "올바른 전화번호 형식이 아닙니다"
    
    @staticmethod
    def validate_business_number(value: str) -> Optional[str]:
        """사업자번호 검증 (10자리)."""
        digits = re.sub(r'\D', '', value)
        if len(digits) == 10:
            return None
        return "사업자번호는 10자리여야 합니다"
    
    @staticmethod
    def validate_email(value: str) -> Optional[str]:
        """이메일 형식 검증."""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if re.match(pattern, value):
            return None
        return "올바른 이메일 형식이 아닙니다"

# 사용
result = extract_from_any_pdf(pdf_path, 1, field_defs)

validator = FieldValidator()
validation_errors = {}

for field_name, data in result["fields"].items():
    value = data["value"]
    
    if field_name == "phone":
        error = validator.validate_phone(value)
    elif field_name == "business_number":
        error = validator.validate_business_number(value)
    elif field_name == "email":
        error = validator.validate_email(value)
    else:
        error = None
    
    if error:
        validation_errors[field_name] = error

if validation_errors:
    print("⚠️ 검증 실패:")
    for field, error in validation_errors.items():
        print(f"  - {field}: {error}")
```

---

## 📦 통합 예제 (Full Stack)

### FastAPI + React 통합

**Backend (FastAPI)**:

```python
# app/api/v1/extraction/router.py

from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
from typing import Dict, Any
import tempfile
from pathlib import Path

router = APIRouter(prefix="/extraction", tags=["extraction"])

# 글로벌 extractor
from app.domain.shared.pdf.unified_extractor import create_production_extractor
extractor = create_production_extractor(enable_ocr=True, gpu=True)

class ExtractionResponse(BaseModel):
    status: str
    fields: Dict[str, Any]
    metadata: Dict[str, Any]

@router.post("/extract-fields", response_model=ExtractionResponse)
async def extract_pdf_fields(
    file: UploadFile = File(...),
    page_num: int = 1,
):
    """PDF에서 필드 추출."""
    
    # 파일 검증
    if not file.filename.endswith('.pdf'):
        raise HTTPException(400, "PDF 파일만 지원됩니다")
    
    # 임시 저장
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        contents = await file.read()
        tmp.write(contents)
        tmp_path = tmp.name
    
    try:
        # 추출
        from app.domain.shared.pdf.unified_extractor import get_standard_field_definitions
        field_defs = get_standard_field_definitions()
        
        result = extractor.extract(tmp_path, page_num, field_defs)
        
        if result["error"]:
            raise HTTPException(500, result["error"])
        
        return ExtractionResponse(
            status="success",
            fields={
                k: {
                    "value": v["value"],
                    "confidence": v["confidence"],
                }
                for k, v in result["fields"].items()
            },
            metadata={
                "pdf_type": result["pdf_type"],
                "extraction_method": result["extraction_method"],
                "filename": file.filename,
            },
        )
    
    finally:
        Path(tmp_path).unlink(missing_ok=True)
```

**Frontend (React)**:

```typescript
// components/PDFExtractor.tsx

import React, { useState } from 'react';
import axios from 'axios';

interface ExtractedField {
  value: string;
  confidence: number;
}

interface ExtractionResult {
  status: string;
  fields: Record<string, ExtractedField>;
  metadata: {
    pdf_type: string;
    extraction_method: string;
    filename: string;
  };
}

export const PDFExtractor: React.FC = () => {
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<ExtractionResult | null>(null);
  const [loading, setLoading] = useState(false);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setFile(e.target.files[0]);
    }
  };

  const handleExtract = async () => {
    if (!file) return;

    setLoading(true);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await axios.post<ExtractionResult>(
        '/api/v1/extraction/extract-fields',
        formData,
        {
          params: { page_num: 1 },
          headers: { 'Content-Type': 'multipart/form-data' },
        }
      );

      setResult(response.data);
    } catch (error) {
      console.error('추출 실패:', error);
      alert('추출에 실패했습니다.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="pdf-extractor">
      <h2>PDF 필드 추출</h2>
      
      <input type="file" accept=".pdf" onChange={handleFileChange} />
      <button onClick={handleExtract} disabled={!file || loading}>
        {loading ? '처리 중...' : '추출 시작'}
      </button>

      {result && (
        <div className="result">
          <h3>추출 결과</h3>
          <p>PDF 타입: {result.metadata.pdf_type}</p>
          <p>추출 방법: {result.metadata.extraction_method}</p>
          
          <table>
            <thead>
              <tr>
                <th>필드</th>
                <th>값</th>
                <th>신뢰도</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(result.fields).map(([field, data]) => (
                <tr key={field}>
                  <td>{field}</td>
                  <td>{data.value}</td>
                  <td>
                    <span className={data.confidence >= 0.7 ? 'high' : 'low'}>
                      {(data.confidence * 100).toFixed(0)}%
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
```

---

## 🔍 디버깅 도구

### 시각화 도구

```python
def visualize_extraction(
    pdf_path: str,
    page_num: int,
    field_definitions: Dict[str, Dict],
    output_image: str = "debug_visualization.png",
):
    """추출 과정을 시각화하여 PNG로 저장.
    
    키워드와 매칭된 값을 bbox와 함께 표시합니다.
    """
    try:
        from PIL import Image, ImageDraw, ImageFont
        import fitz
    except ImportError:
        print("PIL과 PyMuPDF가 필요합니다")
        return
    
    # PDF를 이미지로 렌더링
    doc = fitz.open(pdf_path)
    page = doc[page_num - 1]
    mat = fitz.Matrix(2.0, 2.0)
    pix = page.get_pixmap(matrix=mat)
    
    if pix.alpha:
        pix = fitz.Pixmap(fitz.csRGB, pix)
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    doc.close()
    
    # Draw 객체 생성
    draw = ImageDraw.Draw(img)
    
    # 추출 수행
    from app.domain.shared.pdf.key_value_extractor import MultiKeywordExtractor
    extractor = MultiKeywordExtractor()
    result = extractor.extract_fields(pdf_path, page_num, field_definitions)
    
    # 스케일 (렌더링 2배 확대)
    scale = 2.0
    
    # 모든 단어 그리기 (회색)
    for word_data in result["raw_words"]:
        bbox = word_data["bbox"]
        x0, y0, x1, y1 = [coord * scale for coord in bbox]
        draw.rectangle([x0, y0, x1, y1], outline="gray", width=1)
    
    # 추출된 Key-Value 그리기
    for field_name, field_data in result["fields"].items():
        # Key bbox (파란색)
        key_bbox = field_data["bbox"]["key"]
        x0, y0, x1, y1 = [coord * scale for coord in key_bbox]
        draw.rectangle([x0, y0, x1, y1], outline="blue", width=3)
        draw.text((x0, y0 - 20), f"KEY: {field_name}", fill="blue")
        
        # Value bbox (빨간색)
        val_bbox = field_data["bbox"]["value"]
        x0, y0, x1, y1 = [coord * scale for coord in val_bbox]
        draw.rectangle([x0, y0, x1, y1], outline="red", width=3)
        draw.text((x0, y0 - 20), f"VALUE: {field_data['value']}", fill="red")
        
        # 연결선 (녹색)
        key_center = (
            (key_bbox[0] + key_bbox[2]) / 2 * scale,
            (key_bbox[1] + key_bbox[3]) / 2 * scale,
        )
        val_center = (
            (val_bbox[0] + val_bbox[2]) / 2 * scale,
            (val_bbox[1] + val_bbox[3]) / 2 * scale,
        )
        draw.line([key_center, val_center], fill="green", width=2)
    
    # 저장
    img.save(output_image)
    print(f"✓ 시각화 저장: {output_image}")

# 사용
visualize_extraction(
    "test.pdf",
    1,
    {"name": {"keywords": ["성명"]}, "company": {"keywords": ["회사명"]}},
    "debug_output.png",
)
```

---

## 🎬 단계별 튜토리얼

### 튜토리얼 1: 처음부터 끝까지

```python
# Step 1: 필요한 모듈 import
from app.domain.shared.pdf.unified_extractor import (
    create_production_extractor,
    get_standard_field_definitions,
)

# Step 2: Extractor 생성 (앱 시작 시 한 번)
extractor = create_production_extractor(
    enable_ocr=True,  # OCR 지원
    gpu=True,         # GPU 가속
)

# Step 3: 필드 정의 가져오기
field_defs = get_standard_field_definitions()

# 또는 커스텀 정의
custom_fields = {
    "name": {"keywords": ["성명", "이름"]},
    "company": {"keywords": ["회사명"]},
}

# Step 4: PDF 추출
result = extractor.extract(
    pdf_path="my_document.pdf",
    page_num=1,
    field_definitions=custom_fields,
    auto_fallback=True,  # 실패 시 자동 폴백
)

# Step 5: 결과 확인
if result["error"]:
    print(f"오류 발생: {result['error']}")
else:
    print(f"PDF 타입: {result['pdf_type']}")
    print(f"추출 방법: {result['extraction_method']}")
    
    for field, data in result["fields"].items():
        print(f"{field}: {data['value']}")

# Step 6: 결과 저장 (JSON)
import json

with open("extracted_data.json", 'w', encoding='utf-8') as f:
    output = {
        field: data["value"]
        for field, data in result["fields"].items()
    }
    json.dump(output, f, ensure_ascii=False, indent=2)

print("✓ 저장 완료: extracted_data.json")
```

---

### 튜토리얼 2: 실전 프로젝트 통합

```python
# project_structure.py
"""
프로젝트 구조:

my_app/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI 앱
│   ├── services/
│   │   └── extraction_service.py  # 추출 서비스
│   └── api/
│       └── extraction_router.py   # API 라우터
├── scripts/
│   └── test_extraction.py         # 테스트 스크립트
└── requirements.txt
"""

# 1. 서비스 레이어 (app/services/extraction_service.py)
from app.domain.shared.pdf.unified_extractor import create_production_extractor
from typing import Dict, Any

class PDFExtractionService:
    """PDF 추출 서비스 (싱글톤)."""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.extractor = create_production_extractor(
                enable_ocr=True,
                gpu=True,
            )
        return cls._instance
    
    def extract_fields(
        self,
        pdf_path: str,
        page_num: int,
        field_definitions: Dict[str, Dict[str, Any]],
    ) -> Dict[str, Any]:
        """필드 추출."""
        result = self.extractor.extract(
            pdf_path, page_num, field_definitions, auto_fallback=True
        )
        
        if result["error"]:
            raise Exception(result["error"])
        
        return result

# 2. API 라우터 (app/api/extraction_router.py)
from fastapi import APIRouter, UploadFile, File
from app.services.extraction_service import PDFExtractionService

router = APIRouter()
service = PDFExtractionService()

@router.post("/extract")
async def extract(file: UploadFile = File(...)):
    # (구현은 위 예제 참조)
    pass

# 3. 메인 앱 (app/main.py)
from fastapi import FastAPI
from app.api import extraction_router

app = FastAPI()
app.include_router(extraction_router.router, prefix="/api/v1")

# 4. 실행
# uvicorn app.main:app --reload
```

---

## 🎓 학습 체크리스트

- [ ] PyMuPDF로 텍스트 및 bbox 추출 방법 이해
- [ ] BBox 클래스와 거리 계산 이해
- [ ] 방향 판단 알고리즘 이해
- [ ] 점수 계산 및 가중치 이해
- [ ] KeyValueExtractor 기본 사용
- [ ] UnifiedKeyValueExtractor로 자동 타입 감지
- [ ] OCR 통합 (EasyOCR)
- [ ] 커스텀 필드 정의 작성
- [ ] Post-processing 함수 작성
- [ ] Production 환경 설정
- [ ] 에러 핸들링 및 검증
- [ ] 성능 최적화 (GPU, 캐싱, 배치)

---

## 📞 문의 및 지원

- **GitHub Issues**: (프로젝트 저장소)
- **문서**: `docs/KEY_VALUE_EXTRACTION_GUIDE.md`
- **알고리즘 상세**: `docs/KEY_VALUE_EXTRACTION_ALGORITHM.md`
- **테스트 코드**: `scripts/test_key_value_extraction.py`

---

**작성일**: 2026-02-26  
**버전**: 1.0.0
