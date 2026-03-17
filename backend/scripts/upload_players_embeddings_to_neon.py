"""
players_embeddings.jsonl 을 읽어 NeonDB의 players_embeddings 테이블에 INSERT.

사전 조건:
  1. NeonDB에 players_embeddings 테이블 존재 (alembic upgrade head)
  2. .env 또는 환경변수에 DATABASE_URL 설정

실행 (프로젝트 루트에서):
  python scripts/upload_players_embeddings_to_neon.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
kr_root = ROOT / "api" / "ohgun" / "kr"
sys.path.insert(0, str(kr_root))

JSONL_PATH = ROOT / "data" / "soccer" / "embeddings" / "players_embeddings.jsonl"
DB_EMBEDDING_DIM = 768  # players_embeddings.embedding = Vector(768)


def pad_embedding(emb: list[float], target_dim: int) -> list[float]:
    if len(emb) >= target_dim:
        return emb[:target_dim]
    return emb + [0.0] * (target_dim - len(emb))


def record_to_content(doc: dict) -> str:
    parts = []
    for k in ("id", "player_name", "team_id", "position", "back_no", "nation"):
        v = doc.get(k)
        if v is not None and v != "":
            parts.append(f"{k}: {v}")
    return " | ".join(parts) if parts else str(doc.get("id", ""))


def main() -> None:
    if not JSONL_PATH.exists():
        print(f"[오류] 파일 없음: {JSONL_PATH}")
        sys.exit(1)

    try:
        from core.database import get_db_connection
    except ImportError as e:
        print(f"[오류] core.database import 실패: {e}")
        print("       프로젝트 루트에서 실행하세요: python scripts/upload_players_embeddings_to_neon.py")
        sys.exit(1)

    records = []
    with open(JSONL_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    if not records:
        print("[오류] JSONL에 레코드가 없습니다.")
        sys.exit(1)

    conn = get_db_connection(register_vector_extension=True)
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM players_embeddings")
            for doc in records:
                player_id = str(doc.get("id", ""))
                content = record_to_content(doc)
                emb = doc.get("embedding", [])
                emb_padded = pad_embedding(emb, DB_EMBEDDING_DIM)
                cur.execute(
                    "INSERT INTO players_embeddings (player_id, content, embedding) VALUES (%s, %s, %s::vector)",
                    (player_id, content, emb_padded),
                )
        conn.commit()
        print(f"[완료] players_embeddings 테이블에 {len(records)}건 업로드됨.")
    except Exception as e:
        conn.rollback()
        print(f"[오류] {e}")
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
