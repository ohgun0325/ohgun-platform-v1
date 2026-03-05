# 시멘틱 분류기 사용 가이드

훈련된 KoElectra 모델을 사용하여 **요구사항이 시멘틱인지 비시멘틱인지** 판별하는 방법입니다.

---

## 1. 모델 정보

- **모델 경로**: `artifacts_train/output/semantic-classifier/`
- **태스크**: 이진 분류 (Binary Classification)
- **레이블**:
  - `0` = **비시멘틱** (Non-semantic): 정량적 제약, 성능 요구사항 등
  - `1` = **시멘틱** (Semantic): 기능/행동을 설명하는 요구사항

---

## 2. 사용 방법

### 2-1. Python 코드로 사용

```python
from artifacts_train.predict import SemanticClassifier

# 분류기 초기화
classifier = SemanticClassifier()

# 단일 텍스트 판별
result = classifier.predict("로그인 시 아이디와 비밀번호를 입력받아 인증한다.")
print(result)
# {
#   "text": "로그인 시 아이디와 비밀번호를 입력받아 인증한다.",
#   "label": 1,
#   "label_name": "시멘틱",
#   "confidence": 0.9876
# }

# 확률까지 보기
result = classifier.predict("시스템은 24시간 가동되어야 한다.", return_probabilities=True)
print(result)
# {
#   "text": "시스템은 24시간 가동되어야 한다.",
#   "label": 0,
#   "label_name": "비시멘틱",
#   "confidence": 0.9234,
#   "probabilities": {
#     0: 0.9234,  # 비시멘틱 확률
#     1: 0.0766   # 시멘틱 확률
#   }
# }

# 여러 텍스트 한 번에 판별
texts = [
    "회원 가입 시 이메일 중복 여부를 검사한다.",
    "응답 시간은 3초 이내여야 한다.",
]
results = classifier.predict_batch(texts, return_probabilities=True)
for r in results:
    print(f"{r['text']} → {r['label_name']} ({r['confidence']:.2%})")
```

### 2-2. 명령줄에서 실행

```bash
python artifacts_train/predict.py
```

---

## 3. 질문/답변 예시

### 예시 1: 시멘틱 요구사항

**질문 (입력)**:
```
"로그인 시 아이디와 비밀번호를 입력받아 인증한다."
```

**답변 (출력)**:
```json
{
  "text": "로그인 시 아이디와 비밀번호를 입력받아 인증한다.",
  "label": 1,
  "label_name": "시멘틱",
  "confidence": 0.9876,
  "probabilities": {
    "0": 0.0124,
    "1": 0.9876
  }
}
```

**해석**: "무엇을 어떻게 한다"는 기능 설명이므로 **시멘틱(1)**. 확신도 98.76%.

---

### 예시 2: 비시멘틱 요구사항

**질문 (입력)**:
```
"시스템은 24시간 가동되어야 한다."
```

**답변 (출력)**:
```json
{
  "text": "시스템은 24시간 가동되어야 한다.",
  "label": 0,
  "label_name": "비시멘틱",
  "confidence": 0.9234,
  "probabilities": {
    "0": 0.9234,
    "1": 0.0766
  }
}
```

**해석**: 정량적 제약(24시간)이므로 **비시멘틱(0)**. 확신도 92.34%.

---

### 예시 3: 시멘틱 요구사항 (복합)

**질문 (입력)**:
```
"주문 완료 시 이메일로 영수증을 발송한다."
```

**답변 (출력)**:
```json
{
  "text": "주문 완료 시 이메일로 영수증을 발송한다.",
  "label": 1,
  "label_name": "시멘틱",
  "confidence": 0.9456,
  "probabilities": {
    "0": 0.0544,
    "1": 0.9456
  }
}
```

**해석**: "언제 무엇을 어떻게 한다"는 행동 설명이므로 **시멘틱(1)**. 확신도 94.56%.

---

### 예시 4: 비시멘틱 요구사항 (성능)

**질문 (입력)**:
```
"응답 시간은 3초 이내여야 한다."
```

**답변 (출력)**:
```json
{
  "text": "응답 시간은 3초 이내여야 한다.",
  "label": 0,
  "label_name": "비시멘틱",
  "confidence": 0.9123,
  "probabilities": {
    "0": 0.9123,
    "1": 0.0877
  }
}
```

**해석**: 성능 지표(3초)라는 정량적 제약이므로 **비시멘틱(0)**. 확신도 91.23%.

---

### 예시 5: 시멘틱 요구사항 (조건부)

**질문 (입력)**:
```
"비밀번호 찾기 시 등록된 이메일로 임시 링크를 보낸다."
```

**답변 (출력)**:
```json
{
  "text": "비밀번호 찾기 시 등록된 이메일로 임시 링크를 보낸다.",
  "label": 1,
  "label_name": "시멘틱",
  "confidence": 0.9789,
  "probabilities": {
    "0": 0.0211,
    "1": 0.9789
  }
}
```

**해석**: 조건("비밀번호 찾기 시")과 행동("이메일로 링크 보낸다")이 명시된 기능 설명이므로 **시멘틱(1)**. 확신도 97.89%.

---

### 예시 6: 비시멘틱 요구사항 (제약)

**질문 (입력)**:
```
"화면 해상도는 1920x1080을 지원해야 한다."
```

**답변 (출력)**:
```json
{
  "text": "화면 해상도는 1920x1080을 지원해야 한다.",
  "label": 0,
  "label_name": "비시멘틱",
  "confidence": 0.8890,
  "probabilities": {
    "0": 0.8890,
    "1": 0.1110
  }
}
```

**해석**: 정량적 스펙(1920x1080)이므로 **비시멘틱(0)**. 확신도 88.90%.

---

## 4. 더 많은 예시

| 요구사항 | 예상 판별 | 이유 |
|---------|----------|------|
| "회원 가입 시 이메일 중복 여부를 검사한다." | 시멘틱(1) | 기능 설명 ("무엇을 검사한다") |
| "데이터 백업은 매일 새벽 2시에 수행한다." | 비시멘틱(0) | 정량적 스케줄 (매일, 2시) |
| "장바구니에 담긴 상품을 주문 전에 수량으로 수정할 수 있다." | 시멘틱(1) | 기능 설명 ("수정할 수 있다") |
| "동시 접속자 1만 명을 수용할 수 있어야 한다." | 비시멘틱(0) | 정량적 제약 (1만 명) |

---

## 5. API로 사용하기

FastAPI 등에서 사용하려면:

```python
from fastapi import FastAPI
from artifacts_train.predict import SemanticClassifier

app = FastAPI()
classifier = SemanticClassifier()
classifier.load()  # 서버 시작 시 한 번만 로드

@app.post("/classify")
async def classify_requirement(text: str):
    result = classifier.predict(text, return_probabilities=True)
    return result
```

---

## 6. 주의사항

- **입력 텍스트**: 요구사항 형태의 문장이어야 정확도가 높습니다.
- **최대 길이**: 모델은 최대 256 토큰까지만 처리합니다 (더 긴 텍스트는 자동으로 잘립니다).
- **확신도**: `confidence`가 0.5에 가까우면 모호한 케이스일 수 있습니다. 필요 시 사람이 검토하세요.

---

## 7. 관련 파일

- **훈련 스크립트**: `artifacts_train/train.py`
- **예측 스크립트**: `artifacts_train/predict.py`
- **훈련된 모델**: `artifacts_train/output/semantic-classifier/`
