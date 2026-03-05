# 입찰서류 인감도장/서명 검출 API

## 개요

- **엔드포인트**: `POST /api/v1/detect`
- **입력**: PDF 파일 1개 (multipart/form-data, 필드명 `file`)
- **출력**: 페이지별 stamp/signature 존재 여부, 검출 좌표, 신뢰도(JSON)

## 환경 변수

| 변수 | 설명 | 기본값 |
|------|------|--------|
| `YOLO_MODEL_PATH` | YOLO 모델 파일 경로 (.pt) | `models/stamp_detector/best.pt` |
| `CONF_THRES` | 검출 신뢰도 임계값 (0~1) | `0.35` |
| `RENDER_DPI` | PDF→이미지 렌더링 DPI (200~300) | `250` |
| `MAX_PAGES` | 처리할 최대 페이지 수 | `50` |
| `SAVE_DEBUG_IMAGES` | 디버그용 페이지 이미지 저장 (true/false) | `false` |

## 응답 JSON 스펙

```json
{
  "job_id": "uuid",
  "filename": "example.pdf",
  "num_pages": 3,
  "summary": {
    "has_stamp_any": true,
    "has_signature_any": false,
    "stamp_pages": [0, 2],
    "signature_pages": []
  },
  "pages": [
    {
      "page_index": 0,
      "has_stamp": true,
      "has_signature": false,
      "detections": [
        { "cls": "stamp", "conf": 0.92, "xyxy": [100.0, 200.0, 180.0, 280.0] }
      ]
    }
  ]
}
```

## 실행

```bash
# 의존성 (이미 설치되어 있을 수 있음)
pip install PyMuPDF ultralytics Pillow

# 서버 실행
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
# 또는
python run.py
```

## 테스트 (Postman / curl)

### 정상 요청

```bash
curl -X POST http://localhost:8000/api/v1/detect \
  -F "file=@/path/to/sample.pdf" \
  -H "Content-Type: multipart/form-data"
```

### 비PDF 업로드 (415 예상)

```bash
curl -X POST http://localhost:8000/api/v1/detect \
  -F "file=@/path/to/test.txt"
```

### 모델 미로드 시 (503 예상)

YOLO 모델 파일이 없으면 앱 시작 시 경고 후, 요청 시 503 반환.

```bash
# YOLO_MODEL_PATH를 존재하지 않는 경로로 두고 서버 재시작 후
curl -X POST http://localhost:8000/api/v1/detect \
  -F "file=@/path/to/sample.pdf"
```

## 프론트엔드 (www.ohgun.site)

- **페이지**: `/stamp-detect`
- **환경 변수**: `NEXT_PUBLIC_API_URL=http://localhost:8000` (백엔드 주소)
- 실행: `cd www.ohgun.site && pnpm dev` → http://localhost:3000/stamp-detect
