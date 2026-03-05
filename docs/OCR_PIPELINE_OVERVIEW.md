## OCR 파이프라인 개요 (PyMuPDF → EasyOCR → Gemini)

이 문서는 현재 프로젝트에서 **PDF → 이미지 → OCR → LLM 보정 → 프론트 템플릿**으로 이어지는 흐름을,  
특히 **PyMuPDF** 단계부터 정리한 실행 과정을 설명합니다.

---

## 1. 전체 흐름 요약

```text
PDF 업로드 / 저장
    ↓
[PyMuPDF 렌더링 계층]
    - PDF 페이지 수 확인
    - 각 페이지를 250 DPI 이미지로 렌더링
    ↓ (PIL.Image 리스트)
[OCR 계층 (EasyOCR)]
    - 이미지 배열에서 텍스트 + 신뢰도 추출
    - 전체 문장(full_text) 구성
    ↓
[전처리 계층]
    - 공백 정리, 전화번호/사업자번호/날짜 형식 정규화
    - 패턴 추출 (phone_numbers, business_numbers, dates)
    - 라벨 주변 텍스트 뽑기 (성명/주소/연락처/위임내용 등)
    ↓
[LLM 보정 계층 (Gemini 2.5 Pro)]
    - 입력: field_contexts + 패턴 + 신뢰도 낮은 OCR 조각 일부
    - 출력: 필드별 {value, evidence_text, confidence} + corrections (OCR 오류 보정 리스트)
    ↓
[API 응답]
    - raw_full_text, raw_items, corrected_text, fields, corrections, used_llm
    ↓
[프론트엔드 템플릿 채우기]
    - 1단계: LLM 없이 빠른 OCR 텍스트로 템플릿 채움
    - 2단계: Gemini 보정 완료 시 필드/텍스트를 다시 덮어쓰기
```

---

## 2. PDF 계층: PyMuPDF 렌더링

### 2.1 전략 패턴 (`PDFContext`, `PyMuPDFStrategy`)

- 파일 위치
  - `app/domain/shared/pdf/pdf_context.py`
  - `app/domain/shared/pdf/strategies/pymupdf_strategy.py`

- 핵심 개념
  - `PDFContext.create("pymupdf")` 혹은 `PDFFactory.get_default_for_rendering()` 으로  
    **PyMuPDF 기반 전략**(`PyMuPDFStrategy`)을 생성.
  - 이 전략은 PDF에서 텍스트/메타데이터를 추출하거나,  
    **특정 페이지를 PIL 이미지로 렌더링**하는 역할을 한다.

### 2.2 페이지 렌더링 흐름

- `PyMuPDFStrategy.render_page_to_image(pdf_source, page_num, dpi=250)`
  - `fitz.open(...)` 으로 PDF 로드
  - 지정 페이지를 `dpi/72` 배율로 렌더링
  - `fitz.Pixmap` → `PIL.Image` 로 변환 후 반환

- `app/domain/detect/services/pdf_renderer.py` 의 `render_pdf_to_images(...)`
  - 입력: PDF 바이트 또는 경로, `dpi=250`, `max_pages=50`
  - 모든 페이지를 순회하며 PIL 이미지 리스트 생성
  - (선택) `save_debug_dir` 에 각 페이지 PNG 저장

이 단계까지의 결과는 **페이지별 PIL.Image 리스트**이며,  
이 이미지를 EasyOCR 또는 다른 비전 모델(예: YOLO)에 그대로 넘길 수 있습니다.

---

## 3. 백엔드 OCR 계층: EasyOCR API

### 3.1 EasyOCR 래퍼 (`EasyOCRReader`)

- 파일: `app/domain/shared/ocr/easyocr_reader.py`
- 역할:
  - `easyocr.Reader`를 감싼 래퍼 클래스
  - `extract_full_text(image_path | np.ndarray)` 등으로
    - 텍스트
    - 신뢰도
    - bbox/center (위치 정보)
    를 추출

### 3.2 FastAPI 라우터 (`/api/v1/ocr`, `/api/v1/ocr/with-llm`)

- 파일: `app/api/v1/ocr/ocr_router.py`

#### `/api/v1/ocr`

- 입력: `file` (PNG/JPG/JPEG)
- 처리:
  - `EasyOCRReader` 싱글톤을 `app.state.ocr_reader` 에 캐시
  - 이미지 바이트 → `PIL.Image` → `numpy` 배열
  - `reader.reader.readtext(...)` 호출
  - `(텍스트, 신뢰도)` 리스트와 `full_text` 생성
- 응답:
  - `full_text: str`
  - `items: [{ text, confidence }]`

#### `/api/v1/ocr/with-llm?use_llm=...`

- 입력: `file` + `use_llm` 쿼리 파라미터
  - `use_llm=false`: LLM 없이 OCR + 전처리만 수행 (빠른 응답)
  - `use_llm=true`: Gemini 기반 보정까지 수행
- 처리:
  1. 동일하게 `EasyOCRReader` 로 OCR 수행
  2. `llm_model` 결정
     - `app.state.chat_model` 이 Gemini이면 그대로 사용
     - 아니면 `app.core.llm.gemini.get_chat_model()`로 직접 로드
  3. `ocr_llm_pipeline.run_pipeline(reader, image_bytes, llm_model)` 호출
- 응답 모델 (`OcrWithLlmResponse`):
  - `raw_full_text: str` – OCR 원문 텍스트
  - `raw_items: [{ text, confidence }]`
  - `corrected_text: str | null` – 전처리 + LLM 보정이 반영된 텍스트
  - `fields: { [필드명]: { value, evidence_text, confidence } }`
  - `corrections: [{ original, corrected }]` – 실제로 수정된 OCR 오류 목록
  - `used_llm: bool` – LLM 사용 여부
  - `error: str | null`

---

## 4. 전처리 + LLM 보정 계층

### 4.1 전처리 모듈 (`ocr_preprocessing.py`)

- 파일: `app/domain/shared/ocr/ocr_preprocessing.py`
- 주요 기능:
  - `normalize_phone_number(text)`  
    - `01012345678 → 010-1234-5678` 등 하이픈 자동 추가
  - `normalize_business_number(text)`  
    - `1234567890 → 123-45-67890` 형식 정규화
  - `normalize_date(text)`  
    - `2025년 1월 2일` / `2025-01-02` → `2025.01.02`
  - `extract_phone_numbers / extract_business_numbers / extract_dates`  
    - 패턴 기반 후보 리스트 추출
  - `extract_all_field_contexts(text, field_labels, window_size)`  
    - `"성명"`, `"주소"`, `"연락처"`, `"위임내용"` 등 각 라벨 주변의 짧은 텍스트 조각 추출
  - `preprocess_ocr_text(text)`  
    - 위 과정을 한 번에 수행하여,  
      - 정규화된 텍스트
      - 패턴 딕셔너리 (`phone_numbers`, `business_numbers`, `dates`)
      를 반환

### 4.2 LLM 파이프라인 (`ocr_llm_pipeline.py`)

- 파일: `app/domain/shared/ocr/ocr_llm_pipeline.py`

핵심 함수:

- `run_pipeline(reader, image_bytes, llm_model, min_confidence=0.3)`
  1. EasyOCR로 원문 `full_text`, `items` 추출
  2. `preprocess_ocr_text`로 전처리 + 패턴 추출
  3. `extract_all_field_contexts`로 필드별 컨텍스트 수집
  4. `run_llm_correction(...)` 호출 (llm_model이 있으면)
  5. LLM이 반환한 `fields`와 `corrections`를 적용해 `corrected_text` 생성
  6. 최종 딕셔너리 반환:
     - `raw_full_text`, `raw_items`, `preprocessed_text`
     - `corrected_text`, `fields`, `corrections`, `used_llm`, `error`

- `run_llm_correction(full_text, items, llm_model, preprocessed_text, patterns, field_contexts)`
  - 내부에서 모델 종류를 판별:
    - `ChatGoogleGenerativeAI` (Gemini) → LangChain 메시지(`SystemMessage`, `HumanMessage`) 사용
    - 그 외(`BaseLLMModel` 계열) → Exaone 스타일 메시지 포맷 사용 가능하도록 분기
  - 시스템 프롬프트에서 LLM 역할을 **엄격하게 제한**:
    - OCR에 없는 정보 생성 금지
    - 의미 추론 기반 년도/숫자 조정 금지
    - 허용되는 보정은 **명백한 OCR 오타**와 띄어쓰기 수준
  - 응답 JSON을 `_parse_llm_json_response`로 파싱:

    ```json
    {
      "fields": {
        "회사연락처": {
          "value": "397-6045",
          "evidence_text": "397-6o45",
          "confidence": 0.98
        },
        ...
      },
      "corrections": [
        { "original": "6o45", "corrected": "6045", "reason": "OCR 오류" },
        ...
      ]
    }
    ```

  - `corrections`를 `preprocessed_text`에 적용하여 `corrected_text` 생성

---

## 5. 프론트엔드 계층 (Next.js OCR 페이지)

- 파일: `www.ohgun.site/app/ocr/page.tsx`

### 5.1 상태 구조

- `template`: 최종 폼 값 (담당자이름, 회사명, 사업자번호, 회사연락처, 회사주소, 주요내용, 작성날짜)
- `ocrResult`: `{ full_text, items, used_llm?, corrections? }`
- `isOcrRunning`: OCR 1차 실행 중 여부
- `isLlmCorrecting`: Gemini 보정 중 여부

### 5.2 실행 흐름 (`handleRunOcr`)

1. **1단계: 빠른 OCR만 실행**
   - `POST /api/v1/ocr/with-llm?use_llm=false`
   - 응답에서 `raw_full_text`, `raw_items` 사용
   - `parseOcrToTemplate(raw_full_text)` 으로 라벨 기반 파싱
   - 결과를 `template` 에 채우고 사용자에게 즉시 표시

2. **2단계: 백그라운드 Gemini 보정**
   - `POST /api/v1/ocr/with-llm?use_llm=true`
   - 응답에서:
     - `corrected_text`
     - `fields` (LLM이 매핑한 필드)
     - `corrections` (어떤 OCR 오류가 고쳐졌는지)
   - `used_llm === true` 이고 `fields` 에 `value` 가 있으면,  
     이 값으로 `template` 을 **다시 덮어쓰기**
   - 화면에는:
     - 먼저 “템플릿 칸에 자동으로 채웠습니다” 메시지
     - 보정 중일 때 “Exaone 보정 중...” → (현재는 Gemini지만 문구만 남아 있음)
     - 보정 완료 시 “Exaone 보정이 적용된 결과입니다.” 등의 안내 문구 표시

---

## 6. 요약

- **PyMuPDF 계층**이 PDF를 **페이지별 이미지** 또는 텍스트로 변환하고,
- **EasyOCR 계층**이 이미지에서 **텍스트 + 신뢰도**를 추출한 뒤,
- **전처리 계층**에서 전화번호/사업자번호/날짜를 정규화하고 필드 주변 컨텍스트를 정리하며,
- **Gemini 2.5 Pro 계층**이 **명백한 OCR 오류만 보정하면서 필드를 매핑**합니다.
- 최종적으로, 이 결과는 `/api/v1/ocr/with-llm` 응답을 통해 프론트로 전달되고,  
  Next.js OCR 페이지에서 **템플릿 폼에 자동 채워지는** 구조입니다.

이 문서를 기준으로, 추후 PyMuPDF/전처리/LLM 단계별 성능 개선이나  
새로운 양식(필드)을 추가할 때 각 계층에 어떤 변경이 필요한지 쉽게 추적할 수 있습니다.

