"""팀(team) 데이터용 저장소 레이어.

JSONL로부터 파싱된 레코드를 네온 PostgreSQL의 `team` 테이블에
일괄 upsert(INSERT ... ON CONFLICT DO UPDATE) 하는 역할을 담당합니다.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Set

from psycopg2.extras import execute_batch  # type: ignore[import-untyped]

from app.core.database import get_db_connection


class MissingStadiumError(Exception):
    """team.stadium_id 가 stadium 테이블에 없을 때 발생."""


class TeamRepository:
    """`team` 테이블에 대한 기본 저장소.

    - PK: id (문자열)
    - UPSERT 전략: 동일 id 가 이미 있으면 최신 값으로 갱신
    """

    _COLUMNS = [
        "id",
        "team_id",
        "stadium_id",
        "stadium_numeric_id",
        "region_name",
        "team_name",
        "e_team_name",
        "orig_yyyy",
        "zip_code1",
        "zip_code2",
        "address",
        "ddd",
        "tel",
        "fax",
        "homepage",
        "owner",
    ]

    def _normalize_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """JSONL 한 줄을 DB insert용 dict로 정규화합니다.

        - 미사용 / 알 수 없는 필드는 무시
        - 누락된 컬럼은 None 으로 채움
        """
        normalized: Dict[str, Any] = {}

        # 최소한의 필수 필드: id, team_id, team_name
        team_pk = record.get("id")
        team_id = record.get("team_id")
        team_name = record.get("team_name")

        if not team_pk or not team_id or not team_name:
            # PK 또는 필수 식별자가 없으면 저장 대상에서 제외
            raise ValueError("team record must have `id`, `team_id`, and `team_name`")

        normalized["id"] = str(team_pk)
        normalized["team_id"] = str(team_id)
        normalized["team_name"] = str(team_name)

        # 나머지 필드들 (없으면 None)
        normalized["stadium_id"] = record.get("stadium_id")
        normalized["stadium_numeric_id"] = record.get("stadium_numeric_id")
        normalized["region_name"] = record.get("region_name")
        normalized["e_team_name"] = record.get("e_team_name")
        normalized["orig_yyyy"] = record.get("orig_yyyy")
        normalized["zip_code1"] = record.get("zip_code1")
        normalized["zip_code2"] = record.get("zip_code2")
        normalized["address"] = record.get("address")
        normalized["ddd"] = record.get("ddd")
        normalized["tel"] = record.get("tel")
        normalized["fax"] = record.get("fax")
        normalized["homepage"] = record.get("homepage")
        normalized["owner"] = record.get("owner")

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

    def upsert_teams(self, records: List[Dict[str, Any]]) -> int:
        """여러 팀 레코드를 `team` 테이블에 upsert 합니다.

        Args:
            records: JSONL 한 줄씩 파싱한 dict 리스트

        Returns:
            실제로 INSERT/UPDATE 시도한 레코드 수

        Raises:
            MissingStadiumError: 레코드의 stadium_id 중 stadium 테이블에 없는 값이 있을 때
        """
        requested_stadium_ids: Set[str] = {
            str(r.get("stadium_id"))
            for r in records
            if isinstance(r, dict) and r.get("stadium_id")
        }

        conn = get_db_connection()
        try:
            valid_stadium_ids: Set[str] = set()
            if requested_stadium_ids:
                with conn.cursor() as cur:
                    cur.execute("SELECT stadium_id FROM stadium WHERE stadium_id IS NOT NULL")
                    valid_stadium_ids = {str(row[0]) for row in cur.fetchall() if row[0]}
                missing = requested_stadium_ids - valid_stadium_ids
                if missing:
                    raise MissingStadiumError(
                        "팀 업로드 전에 스타디움(stadium) JSONL을 먼저 업로드해 주세요. "
                        f"stadium 테이블에 없는 stadium_id: {sorted(missing)}"
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
            INSERT INTO team ({cols})
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

