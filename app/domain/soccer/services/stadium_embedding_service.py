"""경기장(stadium) 데이터 → 임베딩 생성 → stadium_embedding 테이블 저장.

Neon DB의 stadium 테이블을 읽어 검색용 텍스트로 만들고,
임베딩 생성 후 stadium_embedding에 넣습니다. RAG/의미 검색용 인덱싱.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from app.core.database import get_db_connection
from app.core.embeddings import generate_embeddings

# stadium_embedding 테이블 컬럼이 vector(1536)이므로 고정
STADIUM_EMBEDDING_DIM = 1536


def _stadium_to_search_text(row: Tuple[Any, ...], columns: List[str]) -> str:
    """DB 한 행을 의미 검색용 한 줄 텍스트로 만듭니다."""
    d = dict(zip(columns, row))
    parts = []
    if d.get("stadium_name"):
        parts.append(f"경기장 {d['stadium_name']}")
    if d.get("stadium_id"):
        parts.append(f"경기장코드 {d['stadium_id']}")
    if d.get("hometeam_id"):
        parts.append(f"홈팀 {d['hometeam_id']}")
    if d.get("seat_count"):
        parts.append(f"좌석수 {d['seat_count']}")
    if d.get("address"):
        parts.append(f"주소 {d['address']}")
    if d.get("tel"):
        parts.append(f"전화번호 {d['tel']}")
    return " ".join(parts) if parts else str(d.get("id", ""))


def index_stadium_embeddings(
    *,
    limit: int | None = None,
    dimension: int = STADIUM_EMBEDDING_DIM,
) -> Dict[str, Any]:
    """stadium 테이블 전부를 읽어 텍스트→임베딩→stadium_embedding에 저장합니다.

    Args:
        limit: 최대 N개만 처리 (None이면 전체)
        dimension: 임베딩 차원 (stadium_embedding 테이블은 1536 고정)

    Returns:
        {"indexed": N, "skipped": 0, "errors": []} 형태의 요약
    """
    conn = get_db_connection(register_vector_extension=True)
    cols = [
        "id", "stadium_id", "stadium_name", "hometeam_id",
        "seat_count", "address", "tel",
    ]
    try:
        with conn.cursor() as cur:
            q = "SELECT " + ", ".join(cols) + " FROM stadium" + (" LIMIT %s" if limit is not None else "")
            cur.execute(q, (limit,) if limit is not None else None)
            rows = cur.fetchall()
    finally:
        conn.close()

    if not rows:
        return {"indexed": 0, "skipped": 0, "errors": [], "message": "처리할 경기장 데이터가 없습니다."}

    texts = [_stadium_to_search_text(r, cols) for r in rows]
    stadium_ids = [str(r[0]) for r in rows]

    embeddings = generate_embeddings(texts, dimension=dimension)
    if len(embeddings) != len(stadium_ids):
        return {
            "indexed": 0,
            "skipped": len(stadium_ids),
            "errors": ["임베딩 개수와 경기장 수가 맞지 않습니다."],
            "message": "임베딩 생성 실패",
        }

    # stadium_embedding.embedding은 vector(dimension) 고정 → 길이 맞춤
    def to_dim(vec: List[float], d: int) -> List[float]:
        if len(vec) >= d:
            return vec[:d]
        return vec + [0.0] * (d - len(vec))

    embeddings = [to_dim(e, dimension) for e in embeddings]

    conn = get_db_connection(register_vector_extension=True)
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM stadium_embedding")
            for sid, emb in zip(stadium_ids, embeddings):
                cur.execute(
                    "INSERT INTO stadium_embedding (stadium_id, embedding) VALUES (%s, %s::vector)",
                    (sid, emb),
                )
        conn.commit()
    except Exception as e:
        conn.rollback()
        return {
            "indexed": 0,
            "skipped": len(stadium_ids),
            "errors": [str(e)],
            "message": "stadium_embedding 저장 중 오류",
        }
    finally:
        conn.close()

    return {
        "indexed": len(stadium_ids),
        "skipped": 0,
        "errors": [],
        "message": f"stadium_embedding에 {len(stadium_ids)}건 인덱싱 완료.",
    }
