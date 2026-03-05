"""선수(player) 데이터용 저장소 레이어.

JSONL로부터 파싱된 레코드를 네온 PostgreSQL의 `player` 테이블에
일괄 upsert(INSERT ... ON CONFLICT DO UPDATE) 하는 역할을 담당합니다.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Set

from psycopg2.extras import execute_batch  # type: ignore[import-untyped]

from app.core.database import get_db_connection


class MissingTeamError(Exception):
    """player.team_id 가 team 테이블에 없을 때 발생하는 예외."""


class PlayerRepository:
    """`player` 테이블에 대한 기본 저장소.

    - PK: id (문자열)
    - UPSERT 전략: 동일 id 가 이미 있으면 최신 값으로 갱신
    """

    _COLUMNS = [
        "id",
        "player_name",
        "team_id",
        "team_numeric_id",
        "e_player_name",
        "nickname",
        "join_yyyy",
        "position",
        "back_no",
        "nation",
        "birth_date",
        "solar",
        "height",
        "weight",
    ]

    def _normalize_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """JSONL 한 줄을 DB insert용 dict로 정규화합니다.

        - 미사용 / 알 수 없는 필드는 무시
        - 누락된 컬럼은 None 으로 채움
        """
        normalized: Dict[str, Any] = {}

        # 최소한의 필수 필드: id, player_name
        player_id = record.get("id") or record.get("player_id")
        player_name = record.get("player_name") or record.get("name")

        if not player_id or not player_name:
            # PK 또는 필수 이름이 없으면 저장 대상에서 제외
            raise ValueError("player record must have both `id` and `player_name`")

        normalized["id"] = str(player_id)
        normalized["player_name"] = str(player_name)

        # 나머지 필드들 (없으면 None)
        normalized["team_id"] = record.get("team_id")
        normalized["team_numeric_id"] = record.get("team_numeric_id")
        normalized["e_player_name"] = record.get("e_player_name")
        normalized["nickname"] = record.get("nickname")
        normalized["join_yyyy"] = record.get("join_yyyy")
        normalized["position"] = record.get("position")
        normalized["back_no"] = record.get("back_no")
        normalized["nation"] = record.get("nation")
        normalized["birth_date"] = record.get("birth_date")
        normalized["solar"] = record.get("solar")
        normalized["height"] = record.get("height")
        normalized["weight"] = record.get("weight")

        return normalized

    def _iter_rows(
        self,
        records: Iterable[Dict[str, Any]],
    ) -> Iterable[Dict[str, Any]]:
        """저장 가능한 레코드만 골라 컬럼 순서에 맞는 dict로 변환."""
        for record in records:
            if not isinstance(record, dict):
                continue
            try:
                normalized = self._normalize_record(record)
            except ValueError:
                # 필수 필드가 없는 레코드는 건너뜀
                continue
            yield {col: normalized.get(col) for col in self._COLUMNS}

    def upsert_players(self, records: List[Dict[str, Any]]) -> int:
        """여러 선수 레코드를 `player` 테이블에 upsert 합니다.

        Args:
            records: JSONL 한 줄씩 파싱한 dict 리스트

        Returns:
            실제로 INSERT/UPDATE 시도한 레코드 수
        """
        # 업로드되는 player 레코드들이 참조하는 team_id 집합
        requested_team_ids: Set[str] = {
            str(r.get("team_id"))
            for r in records
            if isinstance(r, dict) and r.get("team_id")
        }

        conn = get_db_connection()
        try:
            valid_team_ids: Set[str] = set()
            if requested_team_ids:
                # team 테이블에서 현재 존재하는 team_id 목록 조회
                with conn.cursor() as cur:
                    cur.execute("SELECT team_id FROM team")
                    valid_team_ids = {str(row[0]) for row in cur.fetchall() if row[0]}

                # 존재하지 않는 team_id 가 있으면, ERD 순서 위반으로 간주하고 에러
                missing = requested_team_ids - valid_team_ids
                if missing:
                    raise MissingTeamError(
                        "player 업로드 전에 stadium.jsonl, teams.jsonl 을 순서대로 먼저 적재해야 합니다. "
                        f"team 테이블에 존재하지 않는 team_id: {sorted(missing)}"
                    )

            rows = list(self._iter_rows(records))
            if not rows:
                return 0

            cols = ", ".join(self._COLUMNS)
            placeholders = ", ".join([f"%({c})s" for c in self._COLUMNS])
            update_assignments = ", ".join(
                f"{c} = EXCLUDED.{c}" for c in self._COLUMNS if c != "id"
            )

            sql = f"""
            INSERT INTO player ({cols})
            VALUES ({placeholders})
            ON CONFLICT (id) DO UPDATE
            SET {update_assignments}
            """

            with conn.cursor() as cur:
                execute_batch(cur, sql, rows, page_size=1000)
            conn.commit()
        finally:
            conn.close()

        return len(rows)

