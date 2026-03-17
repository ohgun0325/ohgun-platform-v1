"""용어집(ODA 용어사전) 질의용 오케스트레이터.

QuestionClassifier 에서 domain 이 ``term`` 으로 분류된 경우에만 호출된다.
"""

from __future__ import annotations

from typing import Optional

from domain.chat_hub.bases.chat_result import ChatResult
from domain.terms.services.term_service import TermService


class TermOrchestrator:
    """용어집 질의를 처리하는 오케스트레이터."""

    def __init__(self, service: Optional[TermService] = None) -> None:
        self._service = service or TermService()

    async def process(self, question: str) -> ChatResult:
        """질문을 받아 용어사전에서 검색하고, 가장 관련 있는 항목을 반환한다."""
        print(f"📚 [TermOrchestrator] 용어 질의 수신: {question!r}")

        entries = self._service.search_terms(query=question, limit=3, search_type="all")
        if not entries:
            # 추후 일반 RAG 로 fallback 할 수 있도록 meta 에 힌트를 남긴다.
            msg = "해당 질문과 일치하는 ODA 용어를 찾지 못했습니다. 다른 방식으로 다시 질문해 주세요."
            print("⚠️ [TermOrchestrator] 검색 결과 없음")
            return ChatResult(
                answer=msg,
                sources=[],
                meta={"domain": "term", "matched": False},
            )

        best = entries[0]
        parsed = best.parsed_output

        # 간단한 자연어 응답 구성
        description = parsed.description or best.output
        answer = (
            f"'{parsed.korean_name}'(영문: {parsed.english_name or 'N/A'}, "
            f"약어: {parsed.abbreviation or 'N/A'})의 의미는 다음과 같습니다.\n\n"
            f"{description}"
        )

        print(
            "✅ [TermOrchestrator] 용어 매칭 성공",
            {"korean_name": parsed.korean_name, "abbreviation": parsed.abbreviation},
        )

        sources = [
            "oda_term_dictionary",
            f"korean_name={parsed.korean_name}",
            f"abbreviation={parsed.abbreviation or ''}",
        ]

        return ChatResult(
            answer=answer,
            sources=sources,
            meta={"domain": "term", "matched": True},
        )
