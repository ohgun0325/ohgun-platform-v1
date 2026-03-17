"""players.jsonl 전체(480개)를 upsert한 뒤, add=True로 임베딩 보충합니다.

[2차 실행용 - 제한 없음]
- 1차에서 생성된 200개 임베딩은 유지하고, 나머지 280개만 추가합니다.
- player / players_embeddings 테이블을 비우지 않습니다.

사전 조건:
  - team 테이블에 players.jsonl에 나오는 team_id(K01~K12 등)가 이미 있어야 합니다.
  - .env에 DATABASE_URL 설정

실행 (프로젝트 루트에서):
  python scripts/reload_player_table_from_jsonl_full.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
kr_root = ROOT / "api" / "ohgun" / "kr"
if str(kr_root) not in sys.path:
    sys.path.insert(0, str(kr_root))

JSONL_PATH = ROOT / "data" / "soccer" / "players.jsonl"


def main() -> int:
    if not JSONL_PATH.exists():
        print(f"[오류] 파일 없음: {JSONL_PATH}")
        return 1

    try:
        from domain.soccer.repositories.player_repository import (
            PlayerRepository,
            MissingTeamError,
        )
        from domain.soccer.services.player_embedding_service import (
            index_player_embeddings,
        )
        from core.database import get_db_connection
    except ImportError as e:
        print(f"[오류] import 실패: {e}")
        print("       프로젝트 루트에서 실행하세요.")
        return 1

    # JSONL 로드
    records = []
    with open(JSONL_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as e:
                print(f"[경고] JSON 파싱 스킵: {e}")
                continue

    if not records:
        print("[오류] 유효한 레코드가 없습니다.")
        return 1

    print(f"[2차 실행 - 전체 모드] players.jsonl 로드: {len(records)}건")

    # 현재 players_embeddings 상태 확인
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM players_embeddings")
            existing_emb_count = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM player")
            existing_player_count = cur.fetchone()[0]
    finally:
        conn.close()

    print(f"\n[현재 DB 상태]")
    print(f"  - player 테이블: {existing_player_count}건")
    print(f"  - players_embeddings 테이블: {existing_emb_count}건")
    print(f"  → 예상: {existing_player_count - existing_emb_count}건이 임베딩 누락 상태\n")

    print(f"[1/2] player 테이블 upsert 시작...")
    try:
        repo = PlayerRepository()
        upserted = repo.upsert_players(records)
        print(f"[1/2] player 테이블 upsert: {upserted}건 처리 (기존 데이터 유지, 신규/갱신만)")
    except MissingTeamError as e:
        print(f"[오류] {e}")
        print("       stadium.jsonl, teams.jsonl 을 먼저 업로드한 뒤 다시 실행하세요.")
        return 1
    except Exception as e:
        print(f"[오류] upsert 실패: {e}")
        return 1

    print("\n[2/2] 임베딩 보충(add=True) 실행 중...")
    print("  → player 테이블에 있지만 players_embeddings에 없는 선수만 임베딩합니다.")
    print("  → 기존 임베딩은 절대 삭제하지 않습니다.\n")

    result = index_player_embeddings(add=True)

    print(f"\n{'='*60}")
    print(f"[최종 임베딩 결과]")
    print(f"{'='*60}")
    print(f"  ✅ indexed: {result.get('indexed', 0)}건 (새로 추가된 임베딩)")
    print(f"  ⏭️  skipped: {result.get('skipped', 0)}건 (이미 존재하여 건너뜀)")
    print(f"  ❌ errors: {len(result.get('errors', []))}건")
    print(f"  📝 message: {result.get('message', '')}")
    print(f"{'='*60}\n")

    # 최종 상태 확인
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM players_embeddings")
            final_emb_count = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM player")
            final_player_count = cur.fetchone()[0]
    finally:
        conn.close()

    print(f"[최종 DB 상태]")
    print(f"  - player 테이블: {final_player_count}건")
    print(f"  - players_embeddings 테이블: {final_emb_count}건")

    if final_emb_count == final_player_count:
        print(f"\n✅ 검증 성공: 모든 선수({final_player_count}명)가 임베딩되었습니다!")
    else:
        print(f"\n⚠️  불일치: player {final_player_count}건 vs embeddings {final_emb_count}건")

    return 0


if __name__ == "__main__":
    sys.exit(main())
