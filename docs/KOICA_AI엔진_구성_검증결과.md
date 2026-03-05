# KOICA AI 엔진 구성 검증 결과

다이어그램의 **AI 엔진 구성** 섹션에 기재된 기술 표현이 실제 코드와 맞는지 검증한 결과입니다.

---

## 1. 요약

| 구성 요소 | 다이어그램 표기 | 검증 결과 | 권장 수정 |
|-----------|-----------------|-----------|-----------|
| **인감/서명 검출** | YOLO **Model** | ⚠️ 표현 모호 | YOLO는 **라이브러리(프레임워크)** 에 가깝고, 실제 "모델"은 **학습된 가중치 파일(.pt)** 임을 구분해 표기 권장 |
| **OCR 분석** | EasyOCR + **Embed** + LLM | ⚠️ 반만 맞음 | **Embed는 보조 역할**(LLM 입력 컨텍스트 축약). 핵심은 **EasyOCR + LLM** |
| **Excel 분석** | Pandas + Embed | ✅ 맞음 | 문자열 매칭 실패 시 **임베딩 기반 의미 매칭** 사용 — 표기 유지 가능 |

---

## 2. 인감/서명 검출: "YOLO Model" 표현

### 다이어그램
- **인감/서명 검출**: "YOLO Model" 사용

### 코드에서의 사용
- `app/domain/detect/services/stamp_detector.py`  
  - `from ultralytics import YOLO`  
  - `self._model = YOLO(str(self.model_path))`  
  - `model_path` 예: `models/stamp_detector/best.pt`

### 정리
- **YOLO**  
  - 넓은 의미: 객체 검출 **아키텍처/알고리즘** 이름 (You Only Look Once).  
  - 이 프로젝트에서는 **Ultralytics** 라는 **Python 라이브러리**(패키지명 `ultralytics`)를 쓰고, 그 안의 **`YOLO` 클래스**로 모델을 로드합니다.  
  - 따라서 “YOLO”는 **라이브러리(및 그 안의 API)** 에 더 가깝고, “모델”이라고만 쓰면 실제로 무엇을 가리키는지 모호합니다.
- **실제 “모델”**  
  - **학습된 가중치 파일** `best.pt` 가 모델에 해당합니다.  
  - YOLO 클래스는 이 `.pt` 파일을 **로드하는 도구**입니다.

### 결론 및 권장 표기
- 다이어그램에서 “YOLO Model”만 쓰면, **라이브러리(Ultralytics YOLO)** 와 **모델(학습된 .pt)** 이 섞여 보일 수 있습니다.
- **권장**:  
  - **"YOLO(Ultralytics) + 학습된 검출 모델(best.pt)"**  
  - 또는 **"Ultralytics YOLO 라이브러리 + 학습 모델(.pt)"**  
  같이 **라이브러리**와 **모델(가중치)** 를 구분해 적는 것이 정확합니다.

---

## 3. OCR 분석: "EasyOCR + Embed + LLM"

### 다이어그램
- **OCR 분석**: "EasyOCR + Embed + LLM"

### 코드에서의 흐름
- `app/domain/shared/ocr/ocr_llm_pipeline.py`  
  1. **EasyOCR**: 이미지 → 텍스트 추출 (`run_ocr_only` → `reader.reader.readtext`)  
  2. **전처리**: 정규식·패턴 추출, 라벨 주변 텍스트 추출 (`preprocess_ocr_text`, `extract_all_field_contexts`)  
  3. **Embed 사용 지점**: `_shrink_field_contexts_with_embeddings`  
     - 필드별 컨텍스트가 `max_chars`(기본 220자)를 넘을 때만 동작  
     - `get_default_semantic_matcher()` → `rank_candidates`로 **LLM에 넘길 문맥을 줄이기 위해** 관련 세그먼트만 선별  
     - 목적: **토큰 수 절감**, OCR 결과를 “분석”하는 핵심 엔진이 아님  
  4. **LLM**: Gemini(또는 Exaone)로 OCR 보정 및 필드 매핑 (`run_llm_correction`)

### 정리
- **EasyOCR**: 문자 인식의 **핵심** — 맞음.  
- **LLM**: 보정·필드 매핑의 **핵심** — 맞음.  
- **Embed**:  
  - OCR 파이프라인에서 **사용은 함**.  
  - 하지만 역할은 “LLM 입력용 컨텍스트 축약”이며, **문자 인식이나 메인 분석 단계가 아님**.  
  - 따라서 “EasyOCR + Embed + LLM”이라고 나열하면 Embed가 **메인 엔진**처럼 보일 수 있어 **반만 맞는 표현**입니다.

### 결론 및 권장 표기
- **현재 구현 기준**  
  - **"EasyOCR + LLM"** 이 OCR 분석의 핵심 구성.  
  - **"Embed"** 는 선택적 보조(컨텍스트 축약)로만 사용.
- **권장**:  
  - **"EasyOCR + LLM (보조: Embed로 컨텍스트 축약)"**  
  - 또는 **"EasyOCR + LLM"** 으로만 표기하고, 상세 설명에서 “필요 시 임베딩으로 LLM 입력 길이 축소”를 부기.

---

## 4. Excel 분석: "Pandas + Embed"

### 다이어그램
- **Excel 분석**: "Pandas + Embed"

### 코드에서의 흐름
- `app/domain/shared/ms_excel/field_extractor.py`  
  1. **Pandas**: `PandasExcelReader`로 시트 읽기 → DataFrame  
  2. **1차**: 문자열 기반 키워드 매칭 (`_find_keyword_string_based`)  
  3. **2차(폴백)**: 문자열 매칭 실패 시 **임베딩 기반 의미 매칭** (`_find_keyword_semantic_based`)  
     - `get_default_semantic_matcher()` → `rank_candidates`  
     - `SemanticFieldMatcher`는 `SentenceTransformer`(예: dragonkue/multilingual-e5-small-ko-v2)로 **Embed** 사용  
  4. 키워드(또는 매칭된 셀) **주변 셀에서 값 추출** → 템플릿 자동완성용 필드로 반환

### 정리
- **Pandas**: Excel 읽기 및 셀 탐색의 **기반** — 맞음.  
- **Embed**: 필드 라벨과 시트 내 텍스트의 **의미 유사도**로 매칭하는 **핵심 폴백** — 맞음.  
- 따라서 **"Pandas + Embed"** 는 실제 구현과 일치합니다.

### 결론
- **다이어그램 표기 "Pandas + Embed" 유지 가능.**  
- 필요 시 "(문자열 매칭 실패 시 임베딩 의미 매칭)" 정도만 부기하면 더 명확합니다.

---

## 5. 다이어그램 수정 제안 (한 줄 요약)

| 항목 | 현재 다이어그램 | 제안 표기 |
|------|------------------|------------|
| 인감/서명 검출 | YOLO Model | **YOLO(Ultralytics) + 학습 모델(.pt)** 또는 **Ultralytics YOLO + 학습된 검출 모델** |
| OCR 분석 | EasyOCR + Embed + LLM | **EasyOCR + LLM** (보조: Embed로 컨텍스트 축약) |
| Excel 분석 | Pandas + Embed | **Pandas + Embed** (유지) |

---

**검증 일자:** 2026년 3월 1일  
**대상:** AI 엔진 구성 — 인감/서명 검출, OCR 분석, Excel 분석
