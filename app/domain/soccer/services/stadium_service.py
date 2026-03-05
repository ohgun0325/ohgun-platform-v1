"""스타디움 데이터에 대한 규칙 기반(전통적인 서비스) 처리 로직.

업로드된 JSONL 데이터를 도메인 규칙에 따라 검증/전처리하거나,
데이터베이스 저장 로직을 담당하는 계층의 스켈레톤입니다.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.domain.soccer.repositories.stadium_repository import StadiumRepository


class StadiumService:
    """규칙 기반(서비스 레이어) 전략.

    - JSONL에서 파싱된 스타디움 레코드를 검증/요약
    - 휴리스틱(간단한 규칙)에 따라 네온 PostgreSQL `stadium` 테이블에 upsert
    """

    def __init__(self, repository: Optional[StadiumRepository] = None) -> None:
        self.repository = repository or StadiumRepository()

    def validate_and_summarize(
        self,
        records: List[Dict[str, Any]],
        data_type: str,
        file_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """규칙 기반으로 스타디움 데이터를 점검하고, DB에 저장한 뒤 요약 정보를 반환합니다."""

        total = len(records)

        stadium_ids = [r.get("stadium_id") for r in records if isinstance(r, dict)]
        unique_stadium_ids = sorted({s for s in stadium_ids if s})

        hometeam_ids = [r.get("hometeam_id") for r in records if isinstance(r, dict)]
        unique_hometeam_ids = sorted({h for h in hometeam_ids if h})

        # 간단한 결측치/필수 필드 체크 예시
        missing_stadium_name = [
            r.get("id") for r in records if not r.get("stadium_name")
        ]

        # 휴리스틱 저장 로직: 필수 필드(id, stadium_id, stadium_name)가 있는 레코드만 upsert
        stored_count = self.repository.upsert_stadiums(records)

        return {
            "mode": "rule_based",
            "file_name": file_name,
            "data_type": data_type,
            "record_count": total,
            "unique_stadium_count": len(unique_stadium_ids),
            "unique_stadium_ids_sample": unique_stadium_ids[:10],
            "unique_hometeam_count": len(unique_hometeam_ids),
            "unique_hometeam_ids_sample": unique_hometeam_ids[:10],
            "missing_stadium_name_count": len(missing_stadium_name),
            "missing_stadium_ids_sample": missing_stadium_name[:10],
            "db_stored_count": stored_count,
        }
