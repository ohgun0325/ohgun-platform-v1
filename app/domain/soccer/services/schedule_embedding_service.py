"""경기 일정(schedule) 데이터 → 임베딩 생성 → schedule_embedding 테이블 저장.

Neon DB의 schedule 테이블을 읽어 검색용 텍스트로 만들고,
임베딩 생성 후 schedule_embedding에 넣습니다. RAG/의미 검색용 인덱싱.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from app.core.database import get_db_connection
from app.core.embeddings import generate_embeddings

# schedule_embedding 테이블 컬럼이 vector(1536)이므로 고정
SCHEDULE_EMBEDDING_DIM = 1536


def _schedule_to_search_text(row: Tuple[Any, ...], columns: List[str]) -> str:
    """DB 한 행을 의미 검색용 한 줄 텍스트로 만듭니다."""
    d = dict(zip(columns, row))
    parts = []
    if d.get("sche_date"):
        # YYYYMMDD 형식을 YYYY-MM-DD로 변환
        date_str = d["sche_date"]
        if len(date_str) == 8:
            date_str = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
        parts.append(f"경기일자 {date_str}")
    if d.get("hometeam_id"):
        parts.append(f"홈팀 {d['hometeam_id']}")
    if d.get("awayteam_id"):
        parts.append(f"원정팀 {d['awayteam_id']}")
    if d.get("stadium_id"):
        parts.append(f"경기장 {d['stadium_id']}")
    if d.get("home_score") is not None and d.get("away_score") is not None:
        parts.append(f"스코어 {d['home_score']} {d['away_score']}")
    if d.get("gubun"):
        parts.append(f"구분 {d['gubun']}")
    return " ".join(parts) if parts else str(d.get("id", ""))


def index_schedule_embeddings(
    *,
    limit: int | None = None,
    dimension: int = SCHEDULE_EMBEDDING_DIM,
) -> Dict[str, Any]:
    """schedule 테이블 전부를 읽어 텍스트→임베딩→schedule_embedding에 저장합니다.

    Args:
        limit: 최대 N개만 처리 (None이면 전체)
        dimension: 임베딩 차원 (schedule_embedding 테이블은 1536 고정)

    Returns:
        {"indexed": N, "skipped": 0, "errors": []} 형태의 요약
    """
    conn = get_db_connection(register_vector_extension=True)
    cols = [
        "id", "sche_date", "hometeam_id", "awayteam_id",
        "stadium_id", "home_score", "away_score", "gubun",
    ]
    try:
        with conn.cursor() as cur:
            q = "SELECT " + ", ".join(cols) + " FROM schedule" + (" LIMIT %s" if limit is not None else "")
            cur.execute(q, (limit,) if limit is not None else None)
            rows = cur.fetchall()
    finally:
        conn.close()

    if not rows:
        return {"indexed": 0, "skipped": 0, "errors": [], "message": "처리할 경기 일정 데이터가 없습니다."}

    texts = [_schedule_to_search_text(r, cols) for r in rows]
    schedule_ids = [str(r[0]) for r in rows]

    embeddings = generate_embeddings(texts, dimension=dimension)
    if len(embeddings) != len(schedule_ids):
        return {
            "indexed": 0,
            "skipped": len(schedule_ids),
            "errors": ["임베딩 개수와 경기 일정 수가 맞지 않습니다."],
            "message": "임베딩 생성 실패",
        }

    # schedule_embedding.embedding은 vector(dimension) 고정 → 길이 맞춤
    def to_dim(vec: List[float], d: int) -> List[float]:
        if len(vec) >= d:
            return vec[:d]
        return vec + [0.0] * (d - len(vec))

    embeddings = [to_dim(e, dimension) for e in embeddings]

    conn = get_db_connection(register_vector_extension=True)
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM schedule_embedding")
            for sid, emb in zip(schedule_ids, embeddings):
                cur.execute(
                    "INSERT INTO schedule_embedding (schedule_id, embedding) VALUES (%s, %s::vector)",
                    (sid, emb),
                )
        conn.commit()
    except Exception as e:
        conn.rollback()
        return {
            "indexed": 0,
            "skipped": len(schedule_ids),
            "errors": [str(e)],
            "message": "schedule_embedding 저장 중 오류",
        }
    finally:
        conn.close()

    return {
        "indexed": len(schedule_ids),
        "skipped": 0,
        "errors": [],
        "message": f"schedule_embedding에 {len(schedule_ids)}건 인덱싱 완료.",
    }
