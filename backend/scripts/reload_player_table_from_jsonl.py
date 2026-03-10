"""players.jsonl을 upsert한 뒤, add=True 방식으로 player 임베딩을 보충합니다.

- player / players_embeddings 테이블을 비우지 않습니다.
- 신규 또는 갱신된 선수만 index_player_embeddings(add=True)로 임베딩합니다.

사전 조건:
  - team 테이블에 players.jsonl에 나오는 team_id(K01~K12 등)가 이미 있어야 합니다.
  - .env에 DATABASE_URL 설정

실행 (프로젝트 루트에서):
  python scripts/reload_player_table_from_jsonl.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

JSONL_PATH = ROOT / "data" / "soccer" / "players.jsonl"


def main() -> int:
    if not JSONL_PATH.exists():
        print(f"[오류] 파일 없음: {JSONL_PATH}")
        return 1

    try:
        from app.domain.soccer.repositories.player_repository import (
            PlayerRepository,
            MissingTeamError,
        )
        from app.domain.soccer.services.player_embedding_service import (
            index_player_embeddings,
        )
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

    # ========== 검증용: None이면 전체 처리(2차 실행), 200 등 숫자면 해당 건수만 처리(1차 실행) ==========
    LIMIT_FOR_TESTING = None  # 2차: 전체 480건 | 1차 검증 시: 200
    original_count = len(records)
    if LIMIT_FOR_TESTING is not None:
        records = records[:LIMIT_FOR_TESTING]
        print(f"[검증 모드] 전체 {original_count}건 중 최초 {len(records)}건만 처리합니다.")
    # ================================================================================================

    print(f"[1/2] players.jsonl 로드: {len(records)}건")

    try:
        repo = PlayerRepository()
        upserted = repo.upsert_players(records)
        print(f"[2/2] player 테이블 upsert: {upserted}건 처리 (기존 데이터 유지, 신규/갱신만)")
    except MissingTeamError as e:
        print(f"[오류] {e}")
        print("       stadium.jsonl, teams.jsonl 을 먼저 업로드한 뒤 다시 실행하세요.")
        return 1
    except Exception as e:
        print(f"[오류] upsert 실패: {e}")
        return 1

    print("\n[임베딩 보충] add=True 모드로 실행 중...")
    print("  → player 테이블에 있지만 players_embeddings에 없는 선수만 임베딩합니다.")
    # 검증 모드: upsert와 동일하게 임베딩도 최대 200건만 처리 (DB에 480명 있어도 200명만 임베딩)
    embed_limit = LIMIT_FOR_TESTING if (original_count > len(records)) else None
    if embed_limit:
        print(f"  → [검증 모드] 임베딩도 최대 {embed_limit}건으로 제한합니다.")
    result = index_player_embeddings(add=True, limit=embed_limit)
    print(f"\n[임베딩 결과]")
    print(f"  - indexed: {result.get('indexed', 0)}건 (새로 추가)")
    print(f"  - skipped: {result.get('skipped', 0)}건 (이미 존재)")
    print(f"  - errors: {len(result.get('errors', []))}건")
    print(f"  - message: {result.get('message', '')}")
    print("\n✅ 완료되었습니다. (기존 임베딩 유지 + 신규만 추가)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
