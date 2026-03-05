# Soccer 도메인: Exaone이 엠베딩 코드를 Cursor 터미널에서 작성하게 하는 과정

현재 Soccer는 **강결합**(Orchestrator → Tool 직접 호출)이므로 Exaone이 Soccer Tool을 **직접** 호출하지는 않는다.  
대신 **우리가 데이터 경로/스키마를 Exaone에 넘기고**, Exaone이 **엠베딩 생성용 Python 스크립트 코드**를 생성한 뒤,  
그 코드를 **Cursor 터미널에서 실행**하는 방식으로 진행한다.

---

## 경로 정리

- **프로젝트 루트**: `app/exaone/soccer_embeddings.py` 기준 2단계 상위 디렉터리.
- **Exaone 모델**: 프로젝트 루트 기준 **`models/exaone-2.4b`**.  
  다른 경로를 쓰려면 환경변수 `EXAONE_MODEL_DIR` 로 지정 (절대경로 또는 루트 기준 상대경로).
- **생성 스크립트 저장**: **`scripts/soccer_embedding_run.py`** (프로젝트 루트 아래).

**2단계 실행 시 반드시 프로젝트 루트에서 실행**해야 `scripts/soccer_embedding_run.py` 를 찾을 수 있다.

---

## 전체 과정 (2단계)

### 1단계: Exaone으로 엠베딩 코드 생성

Cursor 터미널에서 **프로젝트 루트**로 이동한 뒤 코드 생성 스크립트를 실행한다.

```bash
# 프로젝트 루트로 이동
cd C:\Users\harry\KPMG\langchain

# Exaone이 엠베딩 스크립트 코드 생성 (models/exaone-2.4b 사용)
python app/exaone/soccer_embeddings.py
```

- **하는 일**: Exaone 모델(`models/exaone-2.4b`)을 로드하고, `data/soccer/` JSONL 구조를 프롬프트에 넣어  
  "data/soccer/*.jsonl 을 읽어서 엠베딩을 생성하는 Python 스크립트"를 **생성**한다.
- **결과**: Exaone이 생성한 코드가 **`scripts/soccer_embedding_run.py`** 에 저장된다.  
  (1단계가 성공해야 이 파일이 생기므로, 2단계에서 “파일 없음”이 나오면 1단계를 먼저 실행해야 한다.)

### 2단계: 생성된 스크립트로 엠베딩 실행

**같은 터미널에서 프로젝트 루트를 유지한 채** 생성된 스크립트를 실행한다.

```bash
# 반드시 프로젝트 루트에서 실행
python scripts/soccer_embedding_run.py
```

- **하는 일**: 1단계에서 Exaone이 만든 스크립트가 `data/soccer/players.jsonl` 등 JSONL을 읽고,  
  임베딩 모델로 벡터를 만든 뒤 파일/DB에 저장한다.
- **주의**: `python scripts/soccer_embedding_run.py` 는 **프로젝트 루트**가 현재 디렉터리일 때만 동작한다.  
  다른 디렉터리에서 실행하면 `scripts/soccer_embedding_run.py` 를 찾지 못해 “No such file or directory” 가 난다.

---

## 요약

| 단계 | 명령 (프로젝트 루트에서) | 담당 |
|------|--------------------------|------|
| 1 | `python app/exaone/soccer_embeddings.py` | Exaone이 **엠베딩 코드** 생성 → `scripts/soccer_embedding_run.py` 저장 |
| 2 | `python scripts/soccer_embedding_run.py` | **저장된 코드** 실행 → Cursor 터미널에서 실제 엠베딩 생성 |

- Exaone 모델 경로: **`models/exaone-2.4b`** (프로젝트 루트 기준). 필요 시 `EXAONE_MODEL_DIR` 로 변경.
- 2단계는 **반드시 프로젝트 루트에서** 실행.
