"""경기 일정(schedule) 데이터용 저장소 레이어.

JSONL로부터 파싱된 레코드를 네온 PostgreSQL의 `schedule` 테이블에
일괄 upsert(INSERT ... ON CONFLICT DO UPDATE) 하는 역할을 담당합니다.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List

from psycopg2.extras import execute_batch  # type: ignore[import-untyped]

from app.core.database import get_db_connection


class ScheduleRepository:
    """`schedule` 테이블에 대한 기본 저장소.

    - PK: id (문자열)
    - UPSERT 전략: 동일 id 가 이미 있으면 최신 값으로 갱신
    """

    _COLUMNS = [
        "id",
        "stadium_id",
        "stadium_numeric_id",
        "hometeam_id",
        "hometeam_numeric_id",
        "awayteam_id",
        "awayteam_numeric_id",
    ]

    def _normalize_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """JSONL 한 줄을 DB insert용 dict로 정규화합니다.

        - 미사용 / 알 수 없는 필드는 무시
        - 누락된 컬럼은 None 으로 채움
        """
        normalized: Dict[str, Any] = {}

        # 최소한의 필수 필드: id
        schedule_pk = record.get("id")

        if not schedule_pk:
            # PK가 없으면 저장 대상에서 제외
            raise ValueError("schedule record must have `id`")

        normalized["id"] = str(schedule_pk)

        # 나머지 필드들 (없으면 None)
        normalized["stadium_id"] = record.get("stadium_id")
        normalized["stadium_numeric_id"] = record.get("stadium_numeric_id")
        normalized["hometeam_id"] = record.get("hometeam_id")
        normalized["hometeam_numeric_id"] = record.get("hometeam_numeric_id")
        normalized["awayteam_id"] = record.get("awayteam_id")
        normalized["awayteam_numeric_id"] = record.get("awayteam_numeric_id")

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

    def upsert_schedules(self, records: List[Dict[str, Any]]) -> int:
        """여러 경기 일정 레코드를 `schedule` 테이블에 upsert 합니다.

        Args:
            records: JSONL 한 줄씩 파싱한 dict 리스트

        Returns:
            실제로 INSERT/UPDATE 시도한 레코드 수
        """
        conn = get_db_connection()
        try:
            rows = list(self._iter_rows(records))
            if not rows:
                return 0

            cols = ", ".join(self._COLUMNS)
            placeholders = ", ".join([f"%({c})s" for c in self._COLUMNS])
            update_assignments = ", ".join(
                f"{c} = EXCLUDED.{c}" for c in self._COLUMNS if c != "id"
            )

            sql = f"""
            INSERT INTO schedule ({cols})
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
