# KoICA 데이터 중 시멘틱 여부 판별 훈련에 적합한 JSONL

KoElectra로 **요구사항이 시멘틱인지 아닌지** 이진 분류하는 훈련 목적에서,  
`data/koica_data` 내 어떤 JSONL이 적합한지와 사용 방법을 정리합니다.

---

## 1. 가장 적합한 데이터: `koica_data_train.jsonl` (및 val/test)

**권장 파일**
- **`data/koica_data/koica_data_train.jsonl`**  
- 보조: `koica_data_val.jsonl`, `koica_data_test.jsonl`

**이유**
- **instruction / input / output** 구조로, **질의(요구사항에 가까운 문장) + 답변** 형태입니다.
- 답변(`output`)에 **“(휴리스틱 …)”**이 있으면 규칙/휴리스틱 기반 답변 → **비시멘틱(0)** 로 볼 수 있고,  
  그렇지 않으면 의미·절차가 담긴 답변 → **시멘틱(1)** 로 볼 수 있어, 라벨 추출이 가능합니다.
- 이미 train/val/test로 나뉘어 있어, 그대로 훈련/검증/테스트 분할로 쓰기 좋습니다.

**현재 스키마 예시**
```json
{
  "instruction": "다음 한국국제협력단 ...",
  "input": "질의: ...",
  "output": "(휴리스틱 ...) ... 또는 실제 답변 내용 ..."
}
```

**시멘틱 판별 훈련에 쓰려면**
- `artifacts_train/train.py`는 **`{"text":"...", "label": 0|1}`** 또는 **`{"requirement":"...", "semantic": true|false}`** 형태를 기대합니다.
- 따라서 **전처리**로 아래 둘 중 하나가 필요합니다.
  1. **전처리 스크립트**로  
     `input`(또는 `instruction + "\n" + input`)을 `text`/`requirement`로,  
     `output`이 “(휴리스틱”으로 시작하면 `label=0`/`semantic=false`, 아니면 `label=1`/`semantic=true`로 변환한 JSONL을 만들거나,
  2. **`train.py`의 `load_examples_from_jsonl()`를 확장**해  
     `instruction`/`input`/`output`이 있는 줄을 읽어, 위 규칙으로 `(text, label)`을 만들어 쓰도록 합니다.

---

## 2. 보조로 쓸 수 있는 데이터: 질의응답 세트

**파일**
- **`한국국제협력단_조달계약 규정 안내 서비스 질의응답 세트_20251031.jsonl`**

**이유**
- “질의응답 세트”라 **질의(요구사항처럼 쓸 문장) + 답변** 구조일 가능성이 큽니다.
- 답변이 “규정/절차 설명”이면 시멘틱(1), “키워드 매칭/단순 회신”이면 비시멘틱(0)으로 구분해 라벨을 붙일 수 있다면, 시멘틱 판별용 **추가 학습 데이터**로 활용 가능합니다.
- 스키마가 `instruction`/`input`/`output` 또는 `질의`/`답변`류라면, `koica_data_train.jsonl`과 같은 방식으로 `(text, label)` 형태로 변환하면 됩니다.

---

## 3. 시멘틱 판별에는 부적합한 데이터

| 파일(예시) | 이유 |
|------------|------|
| `한국국제협력단_ODA 용어사전_20230612.jsonl` | 용어+정의 위주 → 대부분 “의미 설명”이라 시멘틱(1)만 많고, 비시멘틱(0) 예시를 만들기 어려움. 시멘틱 예시만 확장할 때만 보조 가능. |
| `한국국제협력단_종료평가보고서 성과지표 요약 데이터_*.jsonl` | 성과지표·요약 등 **정형 통계** 위주 → “요구사항 한 문장” 형태가 아니어서 시멘틱/비시멘틱 구분이 잘 맞지 않음. |
| `한국국제협력단_사업유형별 ODA 실적통계_*.jsonl` | 실적·통계 테이블에 가까움 → 요구사항 문장이 아니라서 비추천. |
| `한국국제협력단_국별 개발협력동향_*.jsonl` 등 | 동향/보도/목록류는 문장 단위 “시멘틱 vs 비시멘틱” 라벨을 붙이기 애매함. |

---

## 4. 요약: 어떤 JSONL을 쓸지

| 목적 | 추천 JSONL | 비고 |
|------|------------|------|
| **시멘틱 여부 판별 훈련** | **`koica_data_train.jsonl`** | instruction/input/output → `(text, label)` 전처리 필요. output에 “(휴리스틱” → 0, 그 외 → 1. |
| 추가 데이터 | `한국국제협력단_조달계약 규정 안내 서비스 질의응답 세트_20251031.jsonl` | 질의를 text로, 답변 유형으로 시멘틱/비시멘틱 라벨 부여 후 사용. |
| 그대로 사용하기엔 부적합 | 용어사전, 성과지표, 실적통계, 동향/목록류 JSONL | 요구사항 문장이 아니거나 한쪽 라벨만 나오기 쉬움. |

---

## 5. 사용 방법 (옵션 B 적용)

**train.py에 KoICA 형식 로더가 들어 있어** 별도 전처리 없이 `koica_data_train.jsonl`을 그대로 넘기면 됩니다.

- `instruction` + `input` → `text`로 사용  
- `output`이 “(휴리스틱”으로 시작하면 **label=0**(비시멘틱), 아니면 **label=1**(시멘틱)

**실행 예시**
```bash
python artifacts_train/train.py --data_path data/koica_data/koica_data_train.jsonl
```

val/test만 쓰고 싶다면:
```bash
python artifacts_train/train.py --data_path data/koica_data/koica_data_val.jsonl
python artifacts_train/train.py --data_path data/koica_data/koica_data_test.jsonl
```

`--model_path`, `--output_dir`, `--num_epochs` 등은 `artifacts_train/train.py`의 인자로 그대로 조정하면 됩니다.
