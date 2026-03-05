"""Soccer 챗용 Tool — 선수/경기/팀/경기장 검색 (직접 연결 구조)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional


def _default_soccer_data_root() -> Path:
    """Soccer JSONL 데이터 루트 (프로젝트 data/soccer)."""
    # app/domain/soccer/tools -> project root = parents[4]
    return Path(__file__).resolve().parents[4] / "data" / "soccer"


def _load_jsonl(path: Path) -> List[Dict[str, Any]]:
    """JSONL 파일을 한 줄씩 파싱해 리스트로 반환."""
    if not path.exists():
        return []
    records: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return records


class PlayerSearchTool:
    """선수 검색 Tool. SoccerOrchestrator가 직접 호출."""

    def __init__(self, data_root: Optional[Path] = None) -> None:
        self._data_root = (data_root or _default_soccer_data_root()).resolve()

    def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """선수명/포지션/팀 등에 query가 포함된 선수 목록 반환."""
        path = self._data_root / "players.jsonl"
        records = _load_jsonl(path)
        if not records:
            return []
        q = query.strip().lower()
        if not q:
            return records[:limit]
        matched: List[Dict[str, Any]] = []
        for r in records:
            if not isinstance(r, dict):
                continue
            name = (r.get("player_name") or "").lower()
            position = (r.get("position") or "").lower()
            team_id = (r.get("team_id") or "").lower()
            if q in name or q in position or q in team_id:
                matched.append(r)
        return matched[:limit]

    def answer(self, query: str, limit: int = 5) -> str:
        """검색 결과를 자연어 요약 문자열로 반환."""
        rows = self.search(query, limit=limit)
        if not rows:
            return "해당 조건에 맞는 선수를 찾지 못했습니다."
        lines = []
        for r in rows:
            name = r.get("player_name", "?")
            position = r.get("position", "")
            team_id = r.get("team_id", "")
            back_no = r.get("back_no", "")
            lines.append(f"- {name} (포지션: {position}, 등번호: {back_no}, 팀: {team_id})")
        return "선수 검색 결과:\n" + "\n".join(lines)


class ScheduleSearchTool:
    """경기 일정 검색 Tool."""

    def __init__(self, data_root: Optional[Path] = None) -> None:
        self._data_root = (data_root or _default_soccer_data_root()).resolve()

    def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """sche_date, hometeam_id, awayteam_id 등에 query가 포함된 경기 목록 반환."""
        path = self._data_root / "schedules.jsonl"
        records = _load_jsonl(path)
        if not records:
            return []
        q = query.strip().lower()
        if not q:
            return records[:limit]
        matched: List[Dict[str, Any]] = []
        for r in records:
            if not isinstance(r, dict):
                continue
            sche_date = str(r.get("sche_date") or "")
            hometeam = (r.get("hometeam_id") or "").lower()
            awayteam = (r.get("awayteam_id") or "").lower()
            if q in sche_date or q in hometeam or q in awayteam:
                matched.append(r)
        return matched[:limit]

    def answer(self, query: str, limit: int = 5) -> str:
        """검색 결과를 자연어 요약 문자열로 반환."""
        rows = self.search(query, limit=limit)
        if not rows:
            return "해당 조건에 맞는 경기 일정을 찾지 못했습니다."
        lines = []
        for r in rows:
            sid = r.get("id", "?")
            date = r.get("sche_date", "?")
            home = r.get("hometeam_id", "?")
            away = r.get("awayteam_id", "?")
            home_s = r.get("home_score", "")
            away_s = r.get("away_score", "")
            score = f" {home_s}:{away_s}" if home_s != "" and away_s != "" else ""
            lines.append(f"- 경기 {sid}: {date} {home} vs {away}{score}")
        return "경기 일정 검색 결과:\n" + "\n".join(lines)


class TeamSearchTool:
    """팀 검색 Tool."""

    def __init__(self, data_root: Optional[Path] = None) -> None:
        self._data_root = (data_root or _default_soccer_data_root()).resolve()

    def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """팀명/지역/team_id에 query가 포함된 팀 목록 반환."""
        path = self._data_root / "teams.jsonl"
        records = _load_jsonl(path)
        if not records:
            return []
        q = query.strip().lower()
        if not q:
            return records[:limit]
        matched: List[Dict[str, Any]] = []
        for r in records:
            if not isinstance(r, dict):
                continue
            name = (r.get("team_name") or "").lower()
            region = (r.get("region_name") or "").lower()
            team_id = (r.get("team_id") or "").lower()
            if q in name or q in region or q in team_id:
                matched.append(r)
        return matched[:limit]

    def answer(self, query: str, limit: int = 5) -> str:
        """검색 결과를 자연어 요약 문자열로 반환."""
        rows = self.search(query, limit=limit)
        if not rows:
            return "해당 조건에 맞는 팀을 찾지 못했습니다."
        lines = []
        for r in rows:
            team_name = r.get("team_name", "?")
            region = r.get("region_name", "")
            team_id = r.get("team_id", "")
            lines.append(f"- {team_name} (지역: {region}, 팀ID: {team_id})")
        return "팀 검색 결과:\n" + "\n".join(lines)


class StadiumSearchTool:
    """경기장 검색 Tool."""

    def __init__(self, data_root: Optional[Path] = None) -> None:
        self._data_root = (data_root or _default_soccer_data_root()).resolve()

    def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """경기장명/주소/stadium_id에 query가 포함된 경기장 목록 반환."""
        path = self._data_root / "stadium.jsonl"
        records = _load_jsonl(path)
        if not records:
            return []
        q = query.strip().lower()
        if not q:
            return records[:limit]
        matched: List[Dict[str, Any]] = []
        for r in records:
            if not isinstance(r, dict):
                continue
            name = (r.get("stadium_name") or "").lower()
            address = (r.get("address") or "").lower()
            sid = (r.get("stadium_id") or "").lower()
            if q in name or q in address or q in sid:
                matched.append(r)
        return matched[:limit]

    def answer(self, query: str, limit: int = 5) -> str:
        """검색 결과를 자연어 요약 문자열로 반환."""
        rows = self.search(query, limit=limit)
        if not rows:
            return "해당 조건에 맞는 경기장을 찾지 못했습니다."
        lines = []
        for r in rows:
            name = r.get("stadium_name", "?")
            address = r.get("address", "")
            seats = r.get("seat_count", "")
            lines.append(f"- {name} (수용인원: {seats}, 주소: {address})")
        return "경기장 검색 결과:\n" + "\n".join(lines)
