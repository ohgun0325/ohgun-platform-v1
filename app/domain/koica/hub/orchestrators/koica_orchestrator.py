"""KOICA 도메인 질문용 오케스트레이터.

- koica_data_test.jsonl 기반 Q&A 매칭
- KoElectra 정책/규칙 분류 (PolicyRuleClassifier)
- MCP 파이프라인 (KoElectra → Exaone)
- KOICA 관련 질문에 대한 Exaone RAG fallback
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from app.domain.chat.bases.chat_result import ChatResult
from app.domain.koica.services.koica_test_qa_service import KoicaTestQAService
from app.domain.koica.services.policy_rule_classifier import PolicyRuleClassifier
from app.domain.chat.orchestrators.rag_orchestrator import run_rag_chat
from app.domain.koica.hub.orchestrators.general_orchestrator import (
    GeneralOrchestrator,
)
from app.domain.koica.mcp.server import KoicaMCPServer
from app.domain.terms.services.term_service import TermService


class KoicaOrchestrator:
    """KOICA 도메인 질의를 처리하는 오케스트레이터.
    
    Soccer의 player_orchestrator, schedule_orchestrator 등과 동일한 역할.
    """

    def __init__(
        self,
        qa_service: Optional[KoicaTestQAService] = None,
        classifier: Optional[PolicyRuleClassifier] = None,
        exaone_model: Optional[Any] = None,  # BaseLLMModel
        term_service: Optional[TermService] = None,
        general_orchestrator: Optional[GeneralOrchestrator] = None,
    ) -> None:
        self._qa_service = qa_service or KoicaTestQAService()
        self._classifier = classifier or PolicyRuleClassifier()
        self._exaone_model = exaone_model
        self._term_service = term_service or TermService()
        # General = Koica 도메인 내부 fallback (데이터셋 없을 때 Exaone/QLoRA/RAG/Gemini)
        self._general_orch = general_orchestrator or GeneralOrchestrator()

        # MCP 서버 초기화 (KoElectra, Exaone, ODA 용어사전 연결)
        try:
            self._mcp_server = KoicaMCPServer(
                koelectra_classifier=self._classifier,
                exaone_model=self._exaone_model,
                term_service=self._term_service,
            )
            print("✅ [KoicaOrchestrator] MCP 서버 초기화 완료")
        except ImportError as e:
            print(f"⚠️ [KoicaOrchestrator] MCP 서버 초기화 실패: {e}")
            self._mcp_server = None
        except Exception as e:
            print(f"⚠️ [KoicaOrchestrator] MCP 서버 초기화 중 오류: {e}")
            self._mcp_server = None

    def set_exaone_model(self, model: Any) -> None:
        """Exaone 모델을 설정하고 MCP 서버에 연결합니다.

        Args:
            model: BaseLLMModel 인스턴스
        """
        self._exaone_model = model
        if self._mcp_server is not None:
            self._mcp_server.set_exaone_model(model)
            print("✅ [KoicaOrchestrator] Exaone 모델이 MCP 서버에 연결되었습니다")

    async def process(self, question: str, context: Dict[str, Any]) -> ChatResult:
        """KOICA 질의 처리.

        - domain=="term" 이면 ODA 용어사전 검색 우선 (Terms = Koica 작은 Star 내부)
        1) koica_data_test.jsonl 에서 유사 Q&A 검색
        2) 매칭 성공 시 해당 output 반환 (+ KoElectra 분류 로그)
        3) 매칭 실패 시 MCP 파이프라인 (KoElectra → Exaone) 시도
        4) MCP 실패 시 Exaone RAG 로 KOICA 관련 답변 생성
        """
        print(f"🏛️ [KoicaOrchestrator] KOICA 질의 수신: {question!r}")

        # Terms(ODA 용어집): KoicaMCPServer 내부 스포크이므로 domain=="term"이면 용어 검색 우선
        if context.get("domain") == "term":
            entries = self._term_service.search_terms(
                query=question, limit=3, search_type="all"
            )
            if entries:
                best = entries[0]
                parsed = best.parsed_output
                description = parsed.description or best.output
                answer = (
                    f"'{parsed.korean_name}'(영문: {parsed.english_name or 'N/A'}, "
                    f"약어: {parsed.abbreviation or 'N/A'})의 의미는 다음과 같습니다.\n\n"
                    f"{description}"
                )
                print(
                    "✅ [KoicaOrchestrator] ODA 용어 매칭 성공",
                    {"korean_name": parsed.korean_name, "abbreviation": parsed.abbreviation},
                )
                return ChatResult(
                    answer=answer,
                    sources=[
                        "oda_term_dictionary",
                        f"korean_name={parsed.korean_name}",
                        f"abbreviation={parsed.abbreviation or ''}",
                    ],
                    meta={"domain": "term", "matched": True},
                )
            # domain=="term"인데 용어 미매칭 시 전용 메시지 반환 (KOICA Q&A로 fallback하지 않음)
            print("⚠️ [KoicaOrchestrator] ODA 용어 검색 결과 없음")
            return ChatResult(
                answer="해당 질문과 일치하는 ODA 용어를 찾지 못했습니다. 다른 방식으로 다시 질문해 주세요.",
                sources=[],
                meta={"domain": "term", "matched": False},
            )

        # context에서 Exaone 모델 받아서 MCP 서버에 연결
        exaone_model = context.get("exaone_model")
        if exaone_model is not None and self._exaone_model != exaone_model:
            self.set_exaone_model(exaone_model)

        # 1) KOICA test셋 기반 Q&A 매칭
        if self._qa_service.is_available():
            hit = self._qa_service.find_best_answer(question)
            if hit is not None:
                answer, score, matched_input = hit

                mode = "policy"
                confidence = 0.0
                if self._classifier.is_available():
                    classification = self._classifier.predict(question)
                    mode = classification["label_name"]
                    confidence = classification["confidence"]

                print(
                    "🧭 [KoicaOrchestrator] KOICA test셋 매칭 응답 반환",
                    {
                        "mode": mode,
                        "match_score": round(score, 3),
                        "koelectra_confidence": round(confidence, 3),
                    },
                )

                return ChatResult(
                    answer=answer,
                    sources=[
                        "koica_data_test.jsonl",
                        f"match_score={score:.3f}",
                        f"matched_input={matched_input[:120]}",
                    ],
                    meta={
                        "domain": "koica",
                        "mode": mode,
                        "match_score": float(score),
                        "koelectra_confidence": float(confidence),
                    },
                )

        # 2) MCP 서버를 통한 KoElectra + Exaone 파이프라인 시도
        if self._mcp_server is not None and self._exaone_model is not None:
            try:
                print("🔗 [KoicaOrchestrator] MCP 파이프라인 실행 (KoElectra → Exaone)...")
                mcp_result = self._mcp_server._classify_and_generate(
                    question=question,
                    system_prompt="당신은 KOICA 업무를 돕는 친절한 AI 어시스턴트입니다.",
                )

                if mcp_result.get("error"):
                    print(f"⚠️ [KoicaOrchestrator] MCP 파이프라인 오류: {mcp_result['error']}")
                else:
                    classification = mcp_result.get("classification", {})
                    response_text = mcp_result.get("response", "")

                    if response_text:
                        print(
                            "🧭 [KoicaOrchestrator] MCP 파이프라인 응답 반환",
                            {
                                "mode": classification.get("label_name", "policy"),
                                "koelectra_confidence": classification.get("confidence", 0.0),
                            },
                        )
                        return ChatResult(
                            answer=response_text,
                            sources=["mcp_pipeline"],
                            meta={
                                "domain": "koica",
                                "mode": classification.get("label_name", "policy"),
                                "koelectra_confidence": classification.get("confidence", 0.0),
                                "pipeline": "koelectra_exaone",
                            },
                        )
            except Exception as e:
                print(f"⚠️ [KoicaOrchestrator] MCP 파이프라인 실행 중 오류: {e}")

        # 3) KOICA Q&A 매칭 실패 → KOICA 관련 RAG 로 fallback
        db_conn = context.get("db_conn")
        embedding_dim = context.get("embedding_dim")
        chat_model = context.get("chat_model")

        if db_conn is not None and embedding_dim is not None and chat_model is not None:
            print("🤖 [KoicaOrchestrator] KOICA RAG 그래프 호출 중...")
            from asyncio import get_running_loop

            loop = get_running_loop()

            def call_rag() -> str:
                return run_rag_chat(
                    user_text=question,
                    chat_model=chat_model,
                    db_conn=db_conn,
                    embedding_dim=embedding_dim,
                    system_prompt="당신은 KOICA 업무를 돕는 친절한 AI 어시스턴트입니다.",
                )

            response_text = await loop.run_in_executor(None, call_rag)

            print(
                "🧭 [KoicaOrchestrator] KOICA RAG 생성 응답 반환",
                {"mode": "policy"},
            )

            return ChatResult(
                answer=response_text,
                sources=[],
                meta={"domain": "koica", "mode": "policy"},
            )

        # 4) 최종 fallback: GeneralOrchestrator (QLoRA → RAG → Gemini, KOICA 맥락)
        # General = Koica 도메인 안의 fallback — 데이터셋에 없을 때 Exaone이 답 생성
        print(
            "🌐 [KoicaOrchestrator] KOICA RAG 컨텍스트 없음 → General fallback (QLoRA/RAG/Gemini)"
        )
        return await self._general_orch.process(question, context)
