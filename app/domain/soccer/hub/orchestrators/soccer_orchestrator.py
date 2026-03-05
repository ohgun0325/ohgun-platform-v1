"""Soccer 도메인 챗 오케스트레이터.

거대한 Star의 스포크 — Tool 직접 연결 구조 (MCP 아님).
선수/경기/팀/경기장 검색 Tool을 직접 호출해 답변을 조합한다.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from app.domain.chat.bases.chat_result import ChatResult
from app.domain.soccer.tools.soccer_tools import (
    PlayerSearchTool,
    ScheduleSearchTool,
    StadiumSearchTool,
    TeamSearchTool,
)


class SoccerOrchestrator:
    """Soccer 도메인 질의를 처리하는 오케스트레이터.

    KoicaOrchestrator와 동일한 레벨의 스포크.
    MCP 서버 없이 Player/Schedule/Team/Stadium Tool을 직접 호출한다.
    """

    # 챗 라우팅용 키워드 — 어떤 Tool을 우선 호출할지 결정
    PLAYER_KEYWORDS = ["선수", "선수들", "player", "등번호", "포지션"]
    SCHEDULE_KEYWORDS = ["경기", "일정", "schedule", "매치", "vs", "대결"]
    TEAM_KEYWORDS = ["팀", "team", "구단", "클럽", "지역"]
    STADIUM_KEYWORDS = ["경기장", "stadium", "구장", "수용인원"]

    def __init__(
        self,
        player_tool: Optional[PlayerSearchTool] = None,
        schedule_tool: Optional[ScheduleSearchTool] = None,
        team_tool: Optional[TeamSearchTool] = None,
        stadium_tool: Optional[StadiumSearchTool] = None,
        data_root: Optional[Path] = None,
    ) -> None:
        root = data_root  # tools 내부에서 None이면 기본 경로 사용
        self._player_tool = player_tool or PlayerSearchTool(data_root=root)
        self._schedule_tool = schedule_tool or ScheduleSearchTool(data_root=root)
        self._team_tool = team_tool or TeamSearchTool(data_root=root)
        self._stadium_tool = stadium_tool or StadiumSearchTool(data_root=root)

    def _which_tool(self, question: str) -> Optional[str]:
        """질문 키워드로 우선 사용할 Tool 이름 반환 (player / schedule / team / stadium)."""
        q = question.strip().lower()
        for kw in self.PLAYER_KEYWORDS:
            if kw in q:
                return "player"
        for kw in self.SCHEDULE_KEYWORDS:
            if kw in q:
                return "schedule"
        for kw in self.TEAM_KEYWORDS:
            if kw in q:
                return "team"
        for kw in self.STADIUM_KEYWORDS:
            if kw in q:
                return "stadium"
        return None

    async def process(self, question: str, context: Dict[str, Any]) -> ChatResult:
        """Soccer 관련 질문을 Tool 직접 호출로 처리해 ChatResult 반환."""
        print(f"⚽ [SoccerOrchestrator] Soccer 질의 수신: {question!r}")

        tool_name = self._which_tool(question)
        limit = int(context.get("soccer_limit", 5))

        if tool_name == "player":
            answer = self._player_tool.answer(question, limit=limit)
            sources = ["soccer_players"]
        elif tool_name == "schedule":
            answer = self._schedule_tool.answer(question, limit=limit)
            sources = ["soccer_schedules"]
        elif tool_name == "team":
            answer = self._team_tool.answer(question, limit=limit)
            sources = ["soccer_teams"]
        elif tool_name == "stadium":
            answer = self._stadium_tool.answer(question, limit=limit)
            sources = ["soccer_stadium"]
        else:
            # 키워드 없으면 선수/팀 검색 우선 시도 후 요약
            a1 = self._player_tool.answer(question, limit=2)
            a2 = self._team_tool.answer(question, limit=2)
            parts = [a1, a2]
            answer = "\n\n".join(p for p in parts if "찾지 못했습니다" not in p)
            if not answer or answer.strip() == "":
                answer = "축구 선수, 팀, 경기 일정, 경기장 중 하나를 질문해 주세요. 예: '김민성 선수 정보', 'K06 팀 정보', '경기 일정'"
            sources = ["soccer_players", "soccer_teams"]

        print("✅ [SoccerOrchestrator] Tool 직접 호출 완료", {"tool": tool_name or "multi"})
        return ChatResult(
            answer=answer,
            sources=sources,
            meta={"domain": "soccer", "tool": tool_name or "multi"},
        )
