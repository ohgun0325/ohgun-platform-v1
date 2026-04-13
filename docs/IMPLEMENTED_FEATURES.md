# 구현·동작 가능 기능 정리

이 문서는 저장소 기준으로 **코드에 구현되어 있고**, 적절한 환경(백엔드 기동, DB, 모델·API 키 등)이 갖춰지면 **실제로 호출·동작할 수 있는 기능**만 정리합니다.  
백엔드 진입점: `backend/api/ohgun/kr/main.py`에 등록된 FastAPI 라우터를 기준으로 합니다.

---

## 1. 동작 전제 (공통)

| 항목 | 설명 |
|------|------|
| **PostgreSQL + pgvector** | Neon 등 DB 연결 정보(`.env` / `core.config`) |
| **채팅·RAG·검색** | DB 연결 필수. 로컬 LLM(QLoRA/Exaone) 또는 Gemini API 키 등 |
| **인감·서명 검출** | `YOLO_MODEL_PATH`(기본 `models/stamp_detector/best.pt`)에 가중치 파일 존재 |
| **OCR** | EasyOCR, 첫 요청 시 리더 로드(GPU 선택). `with-llm`은 Gemini 등 LLM 설정 필요 |
| **RfP 평가** | 업로드·파싱·평가 파이프라인 도메인 코드 동작 |

---

## 2. 백엔드 API (FastAPI)

### 2.1 헬스·벡터 검색 (`domain.shared.router`)

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/health` | DB·임베딩 차원 등 상태 |
| POST | `/search` | 임베딩 생성 후 pgvector 유사 문서 검색 |

### 2.2 KOICA 채팅·보고서 (`api.v1.koica`, prefix `/api/v1/koica`)

| 메서드 | 경로 | 설명 |
|--------|------|------|
| POST | `/api/v1/koica/chat` | KOICA 도메인 질의, `chat_with_ai`(RAG/오케스트레이션) |
| POST | `/api/v1/koica/report/summarize` | 보고서 PDF 업로드 후 요약(구현된 라우터 기준) |

### 2.3 인감·서명 검출 (`api.v1.detect`, prefix `/api/v1/detect`)

| 메서드 | 경로 | 설명 |
|--------|------|------|
| POST | `/api/v1/detect` | PDF/이미지 업로드, YOLO 검출. 모델 미로드 시 503 |

### 2.4 ODA 용어 (`api.v1.term`, prefix `/api/v1/term`)

| 메서드 | 경로 | 설명 |
|--------|------|------|
| POST | `/api/v1/term/search` | 용어 검색 |
| GET | `/api/v1/term/` | 용어 목록 |
| GET | `/api/v1/term/korean/{name}` | 한글명 조회 |
| GET | `/api/v1/term/english/{name}` | 영문명 조회 |
| GET | `/api/v1/term/abbreviation/{abbr}` | 약어 조회 |

### 2.5 관리자·사용자 플로우 (`api.v1.admin.user`, prefix `/api/v1/admin/user`)

| 메서드 | 경로 | 설명 |
|--------|------|------|
| POST | `/api/v1/admin/user` | `UserFlow` 기반 규칙/정책 분기 처리 |

### 2.6 RfP 평가 (`api.v1.evaluation`, prefix `/api/v1/evaluation`)

| 메서드 | 경로 | 설명 |
|--------|------|------|
| POST | `/api/v1/evaluation/rfp/upload` | RfP PDF 업로드·요구사항 추출 |
| POST | `/api/v1/evaluation/proposal/upload` | 제안서 PDF 업로드·파싱 |
| POST | `/api/v1/evaluation/evaluate` | 평가 실행 |
| GET | `/api/v1/evaluation/rfp/{rfp_id}` | RfP 조회 |
| GET | `/api/v1/evaluation/rfp/{rfp_id}/requirements` | 요구사항 목록 |
| GET | `/api/v1/evaluation/rfp/{rfp_id}/requirements/mandatory` | 필수 요구사항 |
| GET | `/api/v1/evaluation/rfp/{rfp_id}/requirements/search` | 요구사항 검색 |
| GET | `/api/v1/evaluation/rfp/{rfp_id}/statistics` | 통계 |
| GET | `/api/v1/evaluation/rfps` | RfP 목록 |

### 2.7 OCR (`api.v1.ocr`, prefix `/api/v1/ocr`)

| 메서드 | 경로 | 설명 |
|--------|------|------|
| POST | `/api/v1/ocr` | 이미지/PDF(첫 페이지) EasyOCR 텍스트 추출 |
| POST | `/api/v1/ocr/with-llm` | 쿼리 `use_llm`: OCR + (선택) LLM 보정·필드 구조화 |

### 2.8 루트

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/` | `static/index.html` 있으면 반환, 없으면 안내 HTML |
| GET | `/docs` | FastAPI Swagger (기본 활성) |

**참고:** `backend/api/ohgun/kr/router/chat_router.py`의 `POST /chat`는 `main.py`에 **포함되어 있지 않습니다**. 통합 채팅은 **`POST /api/v1/koica/chat`** 을 사용합니다.

---

## 3. 도메인·공유 구현 (API 외)

다음은 라우터가 직접 노출하지 않아도 **다른 서비스에서 import 되어 동작**하는 코드입니다.

| 영역 | 위치(예) | 용도 |
|------|-----------|------|
| PDF 키–값 추출 | `domain/shared/pdf/key_value_extractor.py`, `unified_extractor.py` | 텍스트/OCR 기반 필드 매칭 |
| 임베딩·벡터스토어 | `core/embeddings.py`, `core/vectorstore.py` | 검색·RAG |
| KOICA 오케스트레이션 | `core/chat_chain.py`, `domain/koica/...` | 채팅 파이프라인 |
| 문서 검출 | `domain/detect/...` | YOLO·PDF 렌더링 |

---

## 4. 프론트엔드 (Next.js)

`frontend/www` 및 `frontend/admin`은 구조가 유사합니다. 대표 경로와 백엔드 연동은 아래와 같습니다.

| 화면 경로 | 주요 연동 |
|-----------|-----------|
| `/` | 랜딩 |
| `/chat` | 브라우저 → Next `POST /api/v1/chat` → 백엔드 **`POST /api/v1/koica/chat`** (Route Handler 프록시) |
| `/stamp-detect` | `POST /api/v1/detect` (`NEXT_PUBLIC_API_URL`) |
| `/ocr` | `POST /api/v1/ocr/with-llm?use_llm=false\|true` |
| `/terms` | `POST /api/v1/term/search` (프록시 또는 상대 경로) |
| `/evaluation` | `.../evaluation/rfp/upload`, `proposal/upload`, `evaluate` |
| `/report` | `POST /api/v1/koica/report/summarize` |
| `/bidding` | `POST /api/v1/detect` (입찰 UI에서 검출 호출) |
| `/dashboard` | 대시보드 UI(백엔드 고정 엔드포인트는 화면 구현에 따름) |
| `/oauth/callback`, `/oauth/error` | OAuth 콜백·에러 |

용어 일부는 `app/api/v1/term/...` Route Handler로 백엔드에 프록시됩니다.

---

## 5. 모바일 (`app/`)

Flutter 기본 템플릿 수준의 프로젝트로, 위 웹·API와 동일한 수준의 **기능 바인딩은 이 저장소만으로는 전제하지 않습니다.**

---

## 6. 명시적으로 제외된 기능

- **Excel 필드 자동 추출 API** (`/api/v1/excel/...`) 및 전용 UI는 제거된 상태입니다.

---

## 7. 관련 문서

- `docs/KOICA_PROJECT_OVERVIEW.md` — 제품 관점 개요  
- `docs/KOICA_BACKEND_TECH_STACK.md` — 기술 스택·아키텍처 상세(일부 서술은 시점에 따라 코드와 다를 수 있음)  
- `docs/DETECT_STAMP_API.md`, `docs/OCR_PIPELINE_OVERVIEW.md` — 검출·OCR 보조  
- `docs/ENVIRONMENT_SETUP.md`, `docs/DEPLOYMENT.md` — 환경·배포  

---

**갱신 기준:** 저장소의 `main.py` 라우터 등록 및 위 경로 기준. 코드 변경 시 이 파일을 함께 수정하는 것을 권장합니다.
