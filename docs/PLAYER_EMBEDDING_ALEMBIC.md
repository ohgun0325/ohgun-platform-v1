# Player 임베딩 테이블 – Alembic으로 Neon DB에 만들기

## 1. 어떤 데이터를 첨부/준비하면 되는지

Alembic이 **player 임베딩 테이블**을 Neon DB에 생성하려면 아래를 준비하면 됩니다.

### (1) DB 연결 정보

- **위치**: `app/alembic.ini`의 `sqlalchemy.url`
- **형식**: `postgresql://USER:PASSWORD@HOST/DB?sslmode=require`
- 이미 Neon DB URL이 들어가 있으면 별도 첨부는 필요 없습니다.

### (2) 임베딩 벡터 차원

- **위치**: `app/alembic/versions/20260128_0000_player_embedding_table.py` 상단
- **변수**: `EMBEDDING_DIM = 2560`
- **의미**: `player_embedding.embedding` 컬럼의 `vector(차원)` 값
- **바꿔야 하는 경우**:
  - Exaone: `2560` 유지
  - Gemini text-embedding-004: 사용하는 차원값으로 수정 (예: 768)
  - 그 외 모델: 해당 모델의 embedding dimension으로 설정

### (3) player 테이블 존재 여부

- `player_embedding`은 `player(id)`를 FK로 참조합니다.
- **필수**: 이미 다른 마이그레이션으로 `player` 테이블이 생성되어 있어야 합니다.
- Soccer 도메인 마이그레이션이 먼저 적용된 상태에서 이 마이그레이션을 돌리면 됩니다.

### (4) env.py가 로드 가능해야 함

- **위치**: `app/alembic/env.py`
- **역할**: `from app.domain.soccer.models.bases import Base, ...` 로 메타데이터를 불러옵니다.
- `app.domain.soccer.models.bases` 모듈이 없으면 import 에러로 Alembic이 아예 안 뜰 수 있습니다.
- **조치**:
  - 해당 경로에 `bases.py`(및 필요한 테이블 정의)가 있으면 그대로 두고,
  - 없으면 `env.py`에서 해당 import를 try/except로 감싸고, 실패 시 `target_metadata = None`으로 두는 방식으로 우회할 수 있습니다.  
    (이번 player_embedding 마이그레이션은 `op.execute`만 사용하므로, 메타데이터가 없어도 동작합니다.)

---

## 2. 실행 방법

프로젝트 루트에서:

```bash
# 현재 리비전 확인
alembic -c app/alembic.ini current

# player_embedding 테이블까지 마이그레이션 적용
alembic -c app/alembic.ini upgrade head
```

`script_location`이 `app/alembic`이면, 실제로는 예를 들어:

```bash
cd app
alembic current
alembic upgrade head
```

처럼 `app` 디렉터리를 기준으로 실행할 수도 있습니다. (`alembic.ini`의 `script_location`과 `sqlalchemy.url` 설정에 맞춰 조정)

---

## 3. 생성되는 테이블 구조

마이그레이션 후 Neon DB에는 다음과 같은 테이블이 생깁니다.

| 컬럼       | 타입             | 비고                          |
|------------|------------------|-------------------------------|
| id         | BIGSERIAL        | PK                            |
| player_id  | VARCHAR(20)      | FK → player(id), NOT NULL     |
| content    | TEXT             | 임베딩할 원본 텍스트, NOT NULL |
| metadata   | JSONB            | 선택                          |
| embedding  | vector(N)        | N = `EMBEDDING_DIM` (기본 2560) |
| created_at | TIMESTAMPTZ      | 기본 now()                    |

- `player_id`에 일반 인덱스가 생성됩니다.
- `EMBEDDING_DIM <= 2000`일 때만 `embedding` 컬럼에 HNSW 인덱스가 생성됩니다 (Neon 제한).

---

## 4. 요약: “데이터 첨부” 체크리스트

| 항목              | 어디에 / 어떻게 준비하는지                                      |
|-------------------|------------------------------------------------------------------|
| DB URL            | `app/alembic.ini`의 `sqlalchemy.url` (이미 있으면 생략)         |
| 임베딩 차원       | `…/20260128_0000_player_embedding_table.py`의 `EMBEDDING_DIM`   |
| player 테이블     | 기존 soccer 마이그레이션으로 이미 생성된 상태                    |
| env.py 로드 가능  | `app.domain.soccer.models.bases` 존재 또는 env.py try/except 처리 |

위 네 가지를 맞춰 주면, `alembic upgrade head` 한 번으로 Neon DB에 player 임베딩 테이블이 생성됩니다.
