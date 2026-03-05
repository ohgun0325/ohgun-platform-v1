# Soccer 엠베딩 작업 가이드

Neon DB에 stadium/team/player/schedule JSONL이 모두 적재된 뒤, **의미 검색(RAG)** 을 위해 각 엔티티 데이터를 임베딩하는 절차입니다.

---

## 1. 진행 순서 요약

```
[이미 완료] stadium → team → player → schedule 업로드
        ↓
[다음 단계] 각 엔티티 임베딩 인덱싱
  - player → 텍스트 → 임베딩 → player_embedding
  - team → 텍스트 → 임베딩 → team_embedding
  - stadium → 텍스트 → 임베딩 → stadium_embedding
  - schedule → 텍스트 → 임베딩 → schedule_embedding
        ↓
[선택] RAG/검색 API에서 각 embedding 테이블 유사도 검색 후 답변 생성
```

---

## 2. 엠베딩 인덱싱 (지금 할 일)

### 2-0. 전체 엔티티 인덱싱 순서

각 엔티티별로 독립적으로 인덱싱할 수 있으며, 순서는 자유롭습니다:

1. **player** 임베딩 인덱싱
2. **team** 임베딩 인덱싱
3. **stadium** 임베딩 인덱싱
4. **schedule** 임베딩 인덱싱

---

## 2-1. player 엠베딩 인덱싱

#### 동작 방식

- **player** 테이블의 모든 행을 읽어
- 각 선수별로 **검색용 텍스트**를 만듭니다.  
  예: `"선수 김철수 JEONG SAMSOO 포지션 FW 소속팀 K05 대한민국 등번호 10"`
- `app.core.embeddings.generate_embeddings(texts, dimension=1536)` 로 벡터 생성
- **player_embedding** 테이블에 `(player_id, embedding)` 로 저장합니다.  
  (기존 인덱스는 전부 삭제 후, 이번에 만든 임베딩으로 다시 채웁니다.)

#### 실행 방법

**방법 A: API 호출 (권장)**

1. 백엔드 서버 실행 (`python run.py` 등)
2. 아래 중 하나로 호출
   - **전체 인덱싱**
     ```http
     POST http://localhost:8000/api/v10/class/soccer/player/index-embeddings
     ```
   - **최대 N명만**
     ```http
     POST http://localhost:8000/api/v10/class/soccer/player/index-embeddings?limit=100
     ```
3. 응답 예:
   ```json
   {
     "indexed": 50,
     "skipped": 0,
     "errors": [],
     "message": "player_embedding에 50건 인덱싱 완료."
   }
   ```

**방법 B: Swagger UI**

1. `http://localhost:8000/docs` 접속
2. **soccer-player** 섹션에서  
   **POST /api/v10/class/soccer/player/index-embeddings** 선택
3. `limit` 필요 시 입력 후 Execute

**방법 C: curl**

```bash
# 전체
curl -X POST "http://localhost:8000/api/v10/class/soccer/player/index-embeddings"

# 최대 100명
curl -X POST "http://localhost:8000/api/v10/class/soccer/player/index-embeddings?limit=100"
```

---

## 2-2. team 엠베딩 인덱싱

#### 동작 방식

- **team** 테이블의 모든 행을 읽어
- 각 팀별로 **검색용 텍스트**를 만듭니다.  
  예: `"팀 FC서울 FC Seoul 팀코드 K01 지역 서울 창단년도 1983 경기장 D03 주소 ..."`
- `app.core.embeddings.generate_embeddings(texts, dimension=1536)` 로 벡터 생성
- **team_embedding** 테이블에 `(team_id, embedding)` 로 저장합니다.

#### 실행 방법

```http
# 전체 인덱싱
POST http://localhost:8000/api/v10/class/soccer/team/index-embeddings

# 최대 N개만
POST http://localhost:8000/api/v10/class/soccer/team/index-embeddings?limit=100
```

---

## 2-3. stadium 엠베딩 인덱싱

#### 동작 방식

- **stadium** 테이블의 모든 행을 읽어
- 각 경기장별로 **검색용 텍스트**를 만듭니다.  
  예: `"경기장 서울월드컵경기장 경기장코드 D03 홈팀 K01 좌석수 66806 주소 ..."`
- `app.core.embeddings.generate_embeddings(texts, dimension=1536)` 로 벡터 생성
- **stadium_embedding** 테이블에 `(stadium_id, embedding)` 로 저장합니다.

#### 실행 방법

```http
# 전체 인덱싱
POST http://localhost:8000/api/v10/class/soccer/stadium/index-embeddings

# 최대 N개만
POST http://localhost:8000/api/v10/class/soccer/stadium/index-embeddings?limit=100
```

---

## 2-4. schedule 엠베딩 인덱싱

#### 동작 방식

- **schedule** 테이블의 모든 행을 읽어
- 각 경기 일정별로 **검색용 텍스트**를 만듭니다.  
  예: `"경기일자 2024-03-01 홈팀 K01 원정팀 K05 경기장 D03 스코어 2 1 구분 Y"`
- `app.core.embeddings.generate_embeddings(texts, dimension=1536)` 로 벡터 생성
- **schedule_embedding** 테이블에 `(schedule_id, embedding)` 로 저장합니다.

#### 실행 방법

```http
# 전체 인덱싱
POST http://localhost:8000/api/v10/class/soccer/schedule/index-embeddings

# 최대 N개만
POST http://localhost:8000/api/v10/class/soccer/schedule/index-embeddings?limit=100
```

---

## 3. 필요한 전제 조건

- 각 **{entity}_embedding** 테이블이 이미 생성되어 있어야 합니다.  
  → 다음 Alembic 마이그레이션 적용 완료:
  - `app/alembic/versions/20260128_0000_player_embedding_table.py`
  - `app/alembic/versions/20260128_0100_team_embedding_table.py`
  - `app/alembic/versions/20260128_0200_stadium_embedding_table.py`
  - `app/alembic/versions/20260128_0300_schedule_embedding_table.py`
- 각 엔티티 테이블(**player**, **team**, **stadium**, **schedule**)에 인덱싱할 행이 있어야 합니다.
- **pgvector** 확장이 DB에 설치되어 있어야 합니다. (위 마이그레이션에서 `CREATE EXTENSION vector` 수행)

---

## 4. 임베딩 차원과 모델

- 모든 **{entity}_embedding.embedding** 컬럼은 `vector(1536)` 입니다.
- 모든 서비스는 `generate_embeddings(..., dimension=1536)` 을 사용합니다.
- 실제 사용 모델(Exaone / Gemini 등)이 1536이 아니면, 서비스에서 **잘라내기/0 패딩**으로 1536으로 맞춘 뒤 넣습니다.  
  품질이 중요한 경우에는 1536 차원을 지원하는 임베딩 모델을 쓰는 편이 좋습니다.

---

## 5. 관련 파일

| 파일 | 역할 |
|------|------|
| **Player 임베딩** | |
| `app/domain/soccer/services/player_embedding_service.py` | player → 텍스트 → 임베딩 → player_embedding 저장 로직 |
| `app/api/v10/soccer/player_router.py` | `POST /index-embeddings` 엔드포인트 |
| `app/alembic/versions/20260128_0000_player_embedding_table.py` | player_embedding 테이블 정의 |
| **Team 임베딩** | |
| `app/domain/soccer/services/team_embedding_service.py` | team → 텍스트 → 임베딩 → team_embedding 저장 로직 |
| `app/api/v10/soccer/team_router.py` | `POST /index-embeddings` 엔드포인트 |
| `app/alembic/versions/20260128_0100_team_embedding_table.py` | team_embedding 테이블 정의 |
| **Stadium 임베딩** | |
| `app/domain/soccer/services/stadium_embedding_service.py` | stadium → 텍스트 → 임베딩 → stadium_embedding 저장 로직 |
| `app/api/v10/soccer/stadium_router.py` | `POST /index-embeddings` 엔드포인트 |
| `app/alembic/versions/20260128_0200_stadium_embedding_table.py` | stadium_embedding 테이블 정의 |
| **Schedule 임베딩** | |
| `app/domain/soccer/services/schedule_embedding_service.py` | schedule → 텍스트 → 임베딩 → schedule_embedding 저장 로직 |
| `app/api/v10/soccer/schedule_router.py` | `POST /index-embeddings` 엔드포인트 |
| `app/alembic/versions/20260128_0300_schedule_embedding_table.py` | schedule_embedding 테이블 정의 |
| **공통** | |
| `app/core/embeddings.py` | `generate_embeddings()` (Exaone / Gemini / 더미) |

---

## 6. 다음 단계 (선택)

- **의미 검색 API**: 질의 문자열을 임베딩한 뒤 `player_embedding` 에서 코사인 유사도로 상위 k건 조회하고, 해당 player를 join 해서 반환.
- **RAG 연결**: 위 검색 결과를 컨텍스트로 넣어 LLM이 “선수 관련 질의”에 답하도록 연동.

이 단계들의 구현이 필요하면 요청해 주세요.
