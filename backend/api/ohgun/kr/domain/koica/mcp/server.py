"""KOICA MCP 서버 - FastMCP를 사용하여 KoElectra와 Exaone을 연결."""

from __future__ import annotations

from typing import Any, Dict, Optional

try:
    from fastmcp import FastMCP
except ImportError:
    FastMCP = None  # type: ignore

from domain.koica.mcp.tools import (
    ExaoneTool,
    FileSystemTool,
    KoElectraTool,
    OdaTermTool,
)
from domain.koica.services.policy_rule_classifier import PolicyRuleClassifier
from domain.terms.services.term_service import TermService
from artifacts.models.interfaces.base import BaseLLMModel


class KoicaMCPServer:
    """KOICA MCP 서버 - KoElectra와 Exaone을 MCP Tool로 노출."""

    def __init__(
        self,
        koelectra_classifier: Optional[PolicyRuleClassifier] = None,
        exaone_model: Optional[BaseLLMModel] = None,
        term_service: Optional[TermService] = None,
    ) -> None:
        """MCP 서버 초기화.

        Args:
            koelectra_classifier: PolicyRuleClassifier 인스턴스
            exaone_model: Exaone 모델 인스턴스
            term_service: ODA 용어사전 TermService (None이면 새로 생성)
        """
        if FastMCP is None:
            raise ImportError(
                "fastmcp 패키지가 필요합니다: pip install fastmcp>=0.1.0"
            )

        self._koelectra_tool = KoElectraTool(koelectra_classifier)
        self._exaone_tool = ExaoneTool(exaone_model)
        self._fs_tool = FileSystemTool()
        self._oda_term_tool = OdaTermTool(term_service)

        # FastMCP 서버 생성
        self._mcp = FastMCP("KOICA MCP Server")

        # KoElectra Tool 등록
        self._mcp.tool()(self._classify_with_koelectra)

        # Exaone Tool 등록
        self._mcp.tool()(self._generate_with_exaone)

        # 연결된 파이프라인 Tool (KoElectra → Exaone)
        self._mcp.tool()(self._classify_and_generate)

        # 파일시스템 Tool 등록 (os/pathlib → EXAONE)
        self._mcp.tool()(self._filesystem_list_dir)
        self._mcp.tool()(self._filesystem_read_text)
        self._mcp.tool()(self._filesystem_path_exists)

        # ODA 용어사전 Tool 등록 (Terms 도메인 = Koica 작은 Star 내부)
        self._mcp.tool()(self._oda_term_search)

    def _oda_term_search(
        self, query: str, limit: int = 3, search_type: str = "all"
    ) -> Dict[str, Any]:
        """ODA 용어사전에서 검색하는 MCP Tool (Koica ODA 용어집)."""
        return self._oda_term_tool.search_oda_terms(
            query=query, limit=limit, search_type=search_type
        )

    def _filesystem_list_dir(self, path: str = ".") -> Dict[str, Any]:
        """디렉터리 내용 목록을 반환하는 MCP Tool (os/pathlib → EXAONE)."""
        return self._fs_tool.list_dir(path)

    def _filesystem_read_text(
        self, path: str, encoding: str = "utf-8"
    ) -> Dict[str, Any]:
        """파일 내용을 텍스트로 읽는 MCP Tool (pathlib → EXAONE)."""
        return self._fs_tool.read_text(path, encoding)

    def _filesystem_path_exists(self, path: str) -> Dict[str, Any]:
        """경로 존재·파일/디렉터리 여부를 반환하는 MCP Tool."""
        return self._fs_tool.path_exists(path)

    def _classify_with_koelectra(self, text: str) -> Dict[str, Any]:
        """KoElectra로 분류하는 MCP Tool.

        Args:
            text: 분류할 텍스트

        Returns:
            분류 결과
        """
        return self._koelectra_tool.classify_policy_rule(text)

    def _generate_with_exaone(self, messages: list[Dict[str, str]]) -> Dict[str, Any]:
        """Exaone으로 응답 생성하는 MCP Tool.

        Args:
            messages: 메시지 리스트

        Returns:
            생성된 응답
        """
        return self._exaone_tool.generate_response(messages)

    def _classify_and_generate(
        self, question: str, system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """KoElectra로 분류한 후 Exaone으로 응답 생성하는 연결된 파이프라인 Tool.

        Args:
            question: 사용자 질문
            system_prompt: 시스템 프롬프트 (선택)

        Returns:
            {
                "classification": KoElectra 분류 결과,
                "response": Exaone 생성 응답,
                "error": 오류 메시지 (있는 경우),
            }
        """
        # 1) KoElectra로 분류
        classification = self._koelectra_tool.classify_policy_rule(question)
        print(
            f"🔗 [KoicaMCPServer] 파이프라인 실행: 분류={classification.get('label_name')}, "
            f"신뢰도={classification.get('confidence', 0):.3f}"
        )

        # 2) Exaone으로 응답 생성
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": question})

        exaone_result = self._exaone_tool.generate_response(messages)

        return {
            "classification": classification,
            "response": exaone_result.get("response", ""),
            "error": exaone_result.get("error"),
        }

    def set_exaone_model(self, model: BaseLLMModel) -> None:
        """Exaone 모델을 설정합니다.

        Args:
            model: 로드된 BaseLLMModel 인스턴스
        """
        self._exaone_tool.set_model(model)

    def get_server(self) -> FastMCP:
        """FastMCP 서버 인스턴스 반환."""
        return self._mcp

    def run(self, transport: str = "stdio") -> None:
        """MCP 서버를 실행합니다.

        Args:
            transport: 전송 방식 ("stdio" 또는 "sse")
        """
        if transport == "stdio":
            self._mcp.run()
        else:
            raise ValueError(f"지원하지 않는 전송 방식: {transport}")


def create_mcp_server(
    koelectra_classifier: Optional[PolicyRuleClassifier] = None,
    exaone_model: Optional[BaseLLMModel] = None,
    term_service: Optional[TermService] = None,
) -> KoicaMCPServer:
    """KOICA MCP 서버를 생성합니다.

    Args:
        koelectra_classifier: PolicyRuleClassifier 인스턴스
        exaone_model: Exaone 모델 인스턴스
        term_service: ODA 용어사전 TermService (None이면 새로 생성)

    Returns:
        KoicaMCPServer 인스턴스
    """
    return KoicaMCPServer(
        koelectra_classifier=koelectra_classifier,
        exaone_model=exaone_model,
        term_service=term_service,
    )
