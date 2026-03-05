# KOICA 내부 구성(Back end) 검증 결과

첨부하신 시스템 아키텍처 다이어그램의 **내부 구성 (Back end)** 에 해당하는  
**Job Queue**, **요청 라우터**, **보안/인증** 이 현재 KOICA 프로젝트에 어떻게 구현되어 있는지 코드 기준으로 확인한 결과입니다.

---

## 1. 요약

| 구성 요소 | 다이어그램 기대 역할 | 현재 KOICA 구현 상태 | 비고 |
|-----------|------------------------|------------------------|------|
| **Job Queue** | 비동기 처리(작업 큐) | ❌ **미구성** | detect/ocr/excel은 동기 처리 |
| **요청 라우터** | 작업 분배 | ⚠️ **부분** | URL 경로 라우팅만 있음, 별도 “작업 분배” 레이어 없음 |
| **보안/인증** | Security/Authentication | ❌ **미적용** | detect/ocr/excel API에 인증 없음 |

**결론: 다이어그램에 나온 “내부 구성”처럼 Job Queue, 요청 라우터(작업 분배), 보안/인증이 KOICA 문서 처리 플로우(detect, ocr, excel)에는 구성되어 있지 않습니다.**

---

## 2. 상세 검증

### 2.1 Job Queue (작업 큐 / 비동기 처리)

**다이어그램:** “Job Queue” → 비동기 처리

**현재 코드:**

- **인감/서명 검출** (`POST /api/v1/detect`): 요청 수신 → PDF/이미지 변환 → YOLO 검출 → **동기적으로** 응답 반환. 별도 큐 없음.
- **OCR** (`POST /api/v1/ocr`, `POST /api/v1/ocr/with-llm`): 요청 수신 → EasyOCR/LLM 파이프라인 → **동기적으로** 응답 반환. 큐 없음.
- **Excel** (`POST /api/v1/excel/extract-fields`): 요청 수신 → pandas/필드 추출 → **동기적으로** 응답 반환. 큐 없음.

**참고:** 프로젝트 내에 Redis/BullMQ 관련 코드는 있습니다.

- `app/api/shared/redis.py`
  - `BULLMQ_LOGIN_QUEUE_KEY`: 로그인 이벤트용 (Node 연동)
  - `BULLMQ_EMBEDDING_QUEUE_KEY`: **Soccer 도메인** 임베딩 배치 작업용
- 즉, **KOICA 문서 처리(detect, ocr, excel)용 Job Queue는 없음.**

**정리:**  
KOICA 플로우에는 “작업 큐에 넣고 비동기 처리”하는 구성이 없고, 모두 **요청당 동기 처리**입니다.

---

### 2.2 요청 라우터 (작업 분배)

**다이어그램:** “요청 라우터” → 작업 분배

**현재 코드:**

- FastAPI의 일반적인 **URL 기반 라우팅**만 사용 중입니다.
  - `app/main.py`에서 `include_router(detect_router, prefix="/api/v1")` 등으로  
    `/api/v1/detect`, `/api/v1/ocr`, `/api/v1/excel` 등 경로가 매핑됨.
- **단일 진입점에서 “파일/요청 타입을 보고 작업을 분배”하는 별도 요청 라우터(컴포넌트)는 없습니다.**
  - 예: “이 파일은 PDF이므로 detect로, 이미지는 ocr로” 같은 **작업 분배 로직**이 없음.
  - 클라이언트가 이미 `/detect`, `/ocr`, `/excel` 중 하나를 골라 호출하는 구조입니다.

**정리:**  
“요청 라우터”가 의미하는 **작업 분배** 레이어는 없고, **경로별 라우팅만** 있는 상태입니다.

---

### 2.3 보안/인증 (Security/Authentication)

**다이어그램:** “보안/인증” (Security/Authentication)

**현재 코드:**

- **CORS:** `app/main.py`에 `CORSMiddleware`만 추가되어 있음. (CORS는 인증이 아님)
- **JWT/토큰 저장:** `app/api/shared/redis.py`에 `store_access_token`, `get_access_token`, `revoke_access_token` 등이 있으나, **로그인/세션 쪽**에서 사용하는 용도로 보이며,
- **detect / ocr / excel 라우터**에는:
  - `Depends()` 로 인증 의존성 주입 없음
  - `Bearer` / `token` / `verify` 등 검색 시 **해당 API에 대한 인증/검증 로직 없음**

따라서 **인감 검출, OCR, Excel 추출 API는 인증 없이 호출 가능한 상태**입니다.

**정리:**  
다이어그램에 나온 “보안/인증”이 **KOICA 문서 처리 API 앞단에 적용되어 있지 않습니다.**

---

## 3. 현재 KOICA 문서 처리 흐름 (실제 구조)

다이어그램과 비교했을 때, 실제로 동작하는 구조는 다음과 같습니다.

```
[클라이언트]
    │
    │  POST /api/v1/detect  또는  /api/v1/ocr  또는  /api/v1/excel
    ▼
[FastAPI 앱]
    │
    ├─ CORS (전체)
    │
    ├─ URL 라우팅만 (작업 분배 레이어 없음)
    │     ├─ /api/v1/detect  → detect_router
    │     ├─ /api/v1/ocr     → ocr_router
    │     └─ /api/v1/excel   → excel_router
    │
    ├─ 인증 미들웨어/Depends 없음 (detect/ocr/excel)
    │
    └─ 각 라우터 내부에서 동기 처리 후 응답
          ├─ Detect: PDF 렌더 → YOLO 검출
          ├─ OCR: EasyOCR → (선택) LLM 보정
          └─ Excel: pandas → 필드 추출
```

- **Job Queue 없음** → 비동기 처리 없음  
- **요청 라우터(작업 분배) 없음** → URL 라우팅만 존재  
- **보안/인증 없음** → detect/ocr/excel은 인증 없이 호출 가능  

---

## 4. 다이어그램과 맞추려면 (구현 시 참고)

다이어그램의 “내부 구성”과 맞추고 싶다면, 예시적으로 아래를 고려할 수 있습니다.

| 구성 요소 | 권장 방향 (예시) |
|-----------|-------------------|
| **Job Queue** | Redis + Celery 또는 RQ, 또는 기존 BullMQ 확장. detect/ocr/excel 요청을 큐에 넣고 워커에서 처리 후 결과 조회 API 제공. |
| **요청 라우터** | 단일 진입 API(예: `POST /api/v1/process`)에서 파일 타입/메타데이터에 따라 detect / ocr / excel 중 하나로 작업을 분배하는 레이어 추가. |
| **보안/인증** | JWT(또는 기존 Redis 토큰) 검증 미들웨어 또는 FastAPI `Depends()`를 detect/ocr/excel 라우터에 적용하여, 인증된 사용자만 호출 가능하도록 제한. |

이 문서는 “현재 코드 기준으로 다이어그램의 내부 구성이 구현되어 있지 않다”는 것을 확인하기 위한 검증 결과입니다.  
구체적인 설계/구현은 요구사항에 맞춰 별도 정리하는 것이 좋습니다.

---

**검증 일자:** 2026년 3월 1일  
**대상:** KOICA 프로젝트 (detect, ocr, excel API 및 main.py, redis 관련 코드)
