from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class ChatResult:
    """오케스트레이터 간에 공통으로 사용하는 채팅 응답 모델."""

    answer: str
    sources: List[str] = field(default_factory=list)
    meta: Dict[str, Any] = field(default_factory=dict)

