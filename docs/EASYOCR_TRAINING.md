# EasyOCR 모델 훈련 가이드

EasyOCR은 **추론 전용** 라이브러리라서, pip으로 설치한 EasyOCR 안에 "학습 실행" API는 없습니다.  
대신 **Recognition(글자 인식)** 모델만 **Clova AI의 deep-text-recognition-benchmark**로 학습할 수 있고, 학습된 가중치를 나중에 활용하는 방식입니다.

---

## 1. 전체 과정 요약

```
[현재 데이터] data/ocr_data (전체 이미지 + JSON bbox/텍스트)
       │
       ▼ ① 데이터 변환 (bbox 크롭 + gt 파일)
[인식용 데이터] 크롭 이미지들 + train_gt.txt / val_gt.txt
       │
       ▼ ② LMDB 생성 (deep-text-recognition-benchmark 형식)
[LMDB] train.lmdb / val.lmdb
       │
       ▼ ③ Recognition 모델 학습 (deep-text-recognition-benchmark)
[학습된 모델] *.pth (Recognition만)
       │
       ▼ ④ (선택) EasyOCR에서 커스텀 모델로 로드
[추론] 우리 데이터에 맞게 인식 성능 향상
```

- **Detection(글자 영역 찾기)** 은 이 파이프라인에서 학습하지 않습니다.  
  현재 데이터로는 **Recognition(영역이 주어졌을 때 글자 인식)** 만 학습합니다.

---

## 2. 단계별 진행 방법

### 2-1. 데이터 변환 (우리 포맷 → 크롭 + gt)

- **입력**: `data/ocr_data/train`, `data/ocr_data/val` (origin/stock 이미지 + label/stock JSON)
- **출력**:
  - 크롭 이미지 디렉터리 (bbox별로 잘라낸 이미지)
  - `train_gt.txt`, `val_gt.txt`: 한 줄에 `경로\t글자레이블` (탭 구분)

프로젝트에 준비된 스크립트:

```bash
python data/ocr_data/prepare_recognition_data.py
```

- 생성 위치: `data/ocr_data/recognition_crops/` (train/val, 이미지 + gt 파일)

### 2-2. LMDB 생성 (deep-text-recognition-benchmark용)

Clova AI 저장소 클론 후, 포함된 `create_lmdb_dataset.py` 사용:

```bash
git clone https://github.com/clovaai/deep-text-recognition-benchmark
cd deep-text-recognition-benchmark
pip install lmdb opencv-python natsort fire
```

gt 파일 형식: 한 줄에 `이미지경로\t레이블` (탭, UTF-8).  
경로는 `inputPath` 기준 상대 경로.

프로젝트 루트를 `LANGCHAIN_ROOT` 라고 할 때:

```bash
# LMDB 생성 (프로젝트 루트에서)
LANGCHAIN_ROOT="C:\Users\harry\KPMG\langchain"   # 실제 경로로 변경

python create_lmdb_dataset.py \
  --inputPath "$LANGCHAIN_ROOT/data/ocr_data/recognition_crops" \
  --gtFile "$LANGCHAIN_ROOT/data/ocr_data/recognition_crops/train_gt.txt" \
  --outputPath "$LANGCHAIN_ROOT/data/ocr_data/lmdb/train_lmdb"

python create_lmdb_dataset.py \
  --inputPath "$LANGCHAIN_ROOT/data/ocr_data/recognition_crops" \
  --gtFile "$LANGCHAIN_ROOT/data/ocr_data/recognition_crops/val_gt.txt" \
  --outputPath "$LANGCHAIN_ROOT/data/ocr_data/lmdb/val_lmdb"
```

(Windows PowerShell에서는 `$LANGCHAIN_ROOT` 대신 절대 경로를 직접 넣거나 `$env:LANGCHAIN_ROOT` 사용.)

### 2-3. Recognition 모델 학습

같은 저장소에서:

```bash
# 학습 (예: CRNN, 한글 문자 세트 등은 옵션으로 조정)
python train.py \
  --train_data /path/to/train_lmdb \
  --valid_data /path/to/val_lmdb \
  --select_data / \
  --batch_ratio 1.0 \
  --exp_name ocr_korean_finetune
```

- GPU 메모리에 맞게 `batch_size`, `imgH`, `imgW` 등 조정.
- 한글 문자 집합은 `utils.py`의 `character` 등에서 설정해야 합니다.

### 2-4. (선택) EasyOCR에서 커스텀 모델 사용

- 학습 결과 `*.pth`는 **Recognition** 가중치만 포함합니다.
- EasyOCR은 기본적으로 Detection + Recognition을 함께 사용하므로,  
  커스텀 Recognition만 끼워 넣으려면 EasyOCR 소스/래퍼를 수정하거나,  
  해당 벤치마크 저장소의 `test.py`로만 추론하는 방식이 일반적입니다.
- 공식 문서: [EasyOCR - Custom Model](https://github.com/JaidedAI/EasyOCR/blob/master/custom_model.md)

---

## 3. 주의사항

| 항목 | 설명 |
|------|------|
| Detection 미학습 | 글자 영역을 찾는 부분은 그대로 EasyOCR 기본 모델 사용. |
| Recognition만 학습 | bbox가 이미 있을 때, 그 안의 글자를 우리 데이터로 fine-tune. |
| 문자 집합 | 한글/숫자/기호를 반드시 `character` 옵션에 맞춰야 함. |
| 데이터 양 | 1601 train, 200 val → bbox 수만큼 샘플 증가. 수만~수십만 개 가능. |

---

## 4. 요약

1. **데이터 변환**: `prepare_recognition_data.py` 로 크롭 + `train_gt.txt` / `val_gt.txt` 생성.  
2. **LMDB 생성**: `create_lmdb_dataset.py` 로 `train_lmdb`, `val_lmdb` 생성.  
3. **학습**: `deep-text-recognition-benchmark` 의 `train.py` 로 Recognition 모델 학습.  
4. **추론**: 학습된 `.pth`는 해당 벤치마크 또는 EasyOCR 커스텀 모델 방식으로 사용.

이 순서대로 진행하면, 현재 준비한 `data/ocr_data` 로 EasyOCR의 **Recognition** 부분을 훈련할 수 있습니다.
