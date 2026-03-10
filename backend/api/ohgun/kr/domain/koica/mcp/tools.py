"""KOICA MCP Tools - KoElectra, Exaone, 파일시스템(os/pathlib)을 MCP Tool로 노출."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.domain.koica.services.policy_rule_classifier import PolicyRuleClassifier
from app.domain.terms.services.term_service import TermService
from artifacts.models.interfaces.base import BaseLLMModel


def _default_allowed_root() -> Path:
    """EXAONE 파일시스템 Tool이 접근 가능한 루트 디렉터리 (프로젝트 data 폴더)."""
    return Path(__file__).resolve().parents[4] / "data"


class FileSystemTool:
    """os / pathlib 기능을 MCP Tool로 노출. EXAONE이 디렉터리 목록·파일 읽기 등을 사용할 수 있게 함."""

    def __init__(self, allowed_root: Optional[Path] = None) -> None:
        """파일시스템 Tool 초기화.

        Args:
            allowed_root: 접근 허용 루트 경로. None이면 프로젝트 data 폴더.
        """
        self._allowed_root = (allowed_root or _default_allowed_root()).resolve()

    def _resolve_and_validate(self, path: str) -> Optional[Path]:
        """경로를 절대경로로 해석하고, 허용 루트 이내인지 검사. 이내가 아니면 None."""
        try:
            p = (self._allowed_root / path.strip().lstrip("/")).resolve()
            if not str(p).startswith(str(self._allowed_root)):
                return None
            return p
        except Exception:
            return None

    def list_dir(self, path: str = ".") -> Dict[str, Any]:
        """디렉터리 내용 목록을 반환합니다 (os.listdir / pathlib 동등).

        Args:
            path: 디렉터리 경로 (허용 루트 기준 상대 경로, 또는 '.')

        Returns:
            {
                "entries": [{"name": "...", "is_dir": bool}, ...],
                "resolved_path": 절대경로 문자열,
                "error": 오류 메시지 (있는 경우),
            }
        """
        resolved = self._resolve_and_validate(path)
        if resolved is None:
            return {
                "entries": [],
                "resolved_path": "",
                "error": "허용된 루트 밖의 경로이거나 잘못된 경로입니다.",
            }
        if not resolved.exists():
            return {
                "entries": [],
                "resolved_path": str(resolved),
                "error": "경로가 존재하지 않습니다.",
            }
        if not resolved.is_dir():
            return {
                "entries": [],
                "resolved_path": str(resolved),
                "error": "디렉터리가 아닙니다.",
            }
        try:
            entries: List[Dict[str, Any]] = []
            for name in sorted(os.listdir(resolved)):
                full = resolved / name
                entries.append({"name": name, "is_dir": full.is_dir()})
            return {"entries": entries, "resolved_path": str(resolved)}
        except OSError as e:
            return {
                "entries": [],
                "resolved_path": str(resolved),
                "error": str(e),
            }

    def read_text(self, path: str, encoding: str = "utf-8") -> Dict[str, Any]:
        """파일 내용을 텍스트로 읽습니다 (pathlib.Path.read_text 동등).

        Args:
            path: 파일 경로 (허용 루트 기준 상대 경로)
            encoding: 인코딩 (기본 utf-8)

        Returns:
            {
                "content": 파일 내용 문자열,
                "resolved_path": 절대경로 문자열,
                "error": 오류 메시지 (있는 경우),
            }
        """
        resolved = self._resolve_and_validate(path)
        if resolved is None:
            return {
                "content": "",
                "resolved_path": "",
                "error": "허용된 루트 밖의 경로이거나 잘못된 경로입니다.",
            }
        if not resolved.exists():
            return {
                "content": "",
                "resolved_path": str(resolved),
                "error": "경로가 존재하지 않습니다.",
            }
        if resolved.is_dir():
            return {
                "content": "",
                "resolved_path": str(resolved),
                "error": "파일이 아닌 디렉터리입니다.",
            }
        try:
            text = resolved.read_text(encoding=encoding)
            return {"content": text, "resolved_path": str(resolved)}
        except OSError as e:
            return {"content": "", "resolved_path": str(resolved), "error": str(e)}
        except UnicodeDecodeError as e:
            return {"content": "", "resolved_path": str(resolved), "error": f"인코딩 오류: {e}"}

    def path_exists(self, path: str) -> Dict[str, Any]:
        """경로가 존재하는지, 파일인지 디렉터리인지 반환합니다.

        Args:
            path: 경로 (허용 루트 기준 상대 경로)

        Returns:
            {
                "exists": bool,
                "is_file": bool,
                "is_dir": bool,
                "resolved_path": 절대경로 문자열,
                "error": 오류 메시지 (있는 경우),
            }
        """
        resolved = self._resolve_and_validate(path)
        if resolved is None:
            return {
                "exists": False,
                "is_file": False,
                "is_dir": False,
                "resolved_path": "",
                "error": "허용된 루트 밖의 경로이거나 잘못된 경로입니다.",
            }
        try:
            return {
                "exists": resolved.exists(),
                "is_file": resolved.is_file(),
                "is_dir": resolved.is_dir(),
                "resolved_path": str(resolved),
            }
        except OSError as e:
            return {
                "exists": False,
                "is_file": False,
                "is_dir": False,
                "resolved_path": str(resolved),
                "error": str(e),
            }

    @property
    def tool_schema_list_dir(self) -> Dict[str, Any]:
        """list_dir MCP Tool 스키마."""
        return {
            "name": "filesystem_list_dir",
            "description": "허용된 디렉터리 내에서 디렉터리 내용 목록을 반환합니다. os/pathlib의 listdir에 해당.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "디렉터리 경로 (상대, 기본 '.')"},
                },
                "required": [],
            },
        }

    @property
    def tool_schema_read_text(self) -> Dict[str, Any]:
        """read_text MCP Tool 스키마."""
        return {
            "name": "filesystem_read_text",
            "description": "허용된 경로 내의 파일을 텍스트로 읽습니다. pathlib read_text에 해당.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "파일 경로 (상대)"},
                    "encoding": {"type": "string", "description": "인코딩 (기본 utf-8)"},
                },
                "required": ["path"],
            },
        }

    @property
    def tool_schema_path_exists(self) -> Dict[str, Any]:
        """path_exists MCP Tool 스키마."""
        return {
            "name": "filesystem_path_exists",
            "description": "경로가 존재하는지, 파일/디렉터리 여부를 반환합니다.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "경로 (상대)"},
                },
                "required": ["path"],
            },
        }


class OdaTermTool:
    """KOICA ODA 용어사전을 MCP Tool로 노출. KoicaMCPServer 작은 Star의 스포크."""

    def __init__(self, term_service: Optional[TermService] = None) -> None:
        """ODA 용어 Tool 초기화.

        Args:
            term_service: TermService 인스턴스 (None이면 새로 생성)
        """
        self._term_service = term_service or TermService()

    def search_oda_terms(
        self, query: str, limit: int = 3, search_type: str = "all"
    ) -> Dict[str, Any]:
        """ODA 용어사전에서 검색합니다.

        Args:
            query: 검색어
            limit: 최대 결과 수
            search_type: 검색 타입 ('title', 'content', 'all')

        Returns:
            {
                "entries": [{"korean_name": ..., "english_name": ..., "abbreviation": ..., "description": ...}, ...],
                "count": 결과 수,
                "error": 오류 메시지 (있는 경우),
            }
        """
        try:
            entries = self._term_service.search_terms(
                query=query, limit=limit, search_type=search_type
            )
            list_dict: List[Dict[str, Any]] = [
                entry.to_dict() for entry in entries
            ]
            print(
                f"📚 [OdaTermTool] ODA 용어 검색: query={query!r}, count={len(list_dict)}"
            )
            return {"entries": list_dict, "count": len(list_dict)}
        except Exception as e:
            error_msg = str(e)
            print(f"⚠️ [OdaTermTool] ODA 용어 검색 실패: {error_msg}")
            return {"entries": [], "count": 0, "error": error_msg}


class KoElectraTool:
    """KoElectra (PolicyRuleClassifier)를 MCP Tool로 노출."""

    def __init__(self, classifier: Optional[PolicyRuleClassifier] = None) -> None:
        """KoElectra Tool 초기화.

        Args:
            classifier: PolicyRuleClassifier 인스턴스 (None이면 새로 생성)
        """
        self._classifier = classifier or PolicyRuleClassifier()
        if not self._classifier.is_available():
            self._classifier.load()

    def classify_policy_rule(self, text: str) -> Dict[str, Any]:
        """정책/규칙 분류를 수행합니다.

        Args:
            text: 분류할 텍스트

        Returns:
            {
                "label": 0(규칙기반) 또는 1(정책기반),
                "label_name": "rule_based" 또는 "policy",
                "confidence": 확신도 (0.0 ~ 1.0),
            }
        """
        if not self._classifier.is_available():
            return {
                "label": 1,
                "label_name": "policy",
                "confidence": 0.5,
                "error": "KoElectra 모델을 사용할 수 없습니다.",
            }

        result = self._classifier.predict(text)
        print(f"🔍 [KoElectraTool] 분류 결과: {result}")
        return result

    @property
    def tool_schema(self) -> Dict[str, Any]:
        """MCP Tool 스키마 반환."""
        return {
            "name": "koelectra_classify",
            "description": "KoElectra 모델을 사용하여 질문을 정책기반(policy) 또는 규칙기반(rule_based)으로 분류합니다.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "분류할 텍스트 (사용자 질문 또는 요구사항)",
                    },
                },
                "required": ["text"],
            },
        }


class ExaoneTool:
    """Exaone 모델을 MCP Tool로 노출."""

    def __init__(self, model: Optional[BaseLLMModel] = None) -> None:
        """Exaone Tool 초기화.

        Args:
            model: BaseLLMModel 인스턴스 (None이면 로드되지 않은 상태)
        """
        self._model = model

    def generate_response(self, messages: list[Dict[str, str]]) -> Dict[str, Any]:
        """Exaone 모델로 응답을 생성합니다.

        Args:
            messages: 메시지 리스트, 각 메시지는 {"role": "user|assistant|system", "content": "..."} 형식

        Returns:
            {
                "response": 생성된 응답 텍스트,
                "error": 오류 메시지 (있는 경우),
            }
        """
        if self._model is None or not self._model.is_loaded:
            return {
                "response": "",
                "error": "Exaone 모델이 로드되지 않았습니다.",
            }

        try:
            response_text = self._model.invoke(messages)
            print(f"🤖 [ExaoneTool] 응답 생성 완료: {len(response_text)}자")
            return {"response": response_text}
        except Exception as e:
            error_msg = str(e)
            print(f"❌ [ExaoneTool] 응답 생성 실패: {error_msg}")
            return {"response": "", "error": error_msg}

    def set_model(self, model: BaseLLMModel) -> None:
        """Exaone 모델을 설정합니다.

        Args:
            model: 로드된 BaseLLMModel 인스턴스
        """
        self._model = model
        print(f"✅ [ExaoneTool] Exaone 모델 설정 완료 (로드됨: {model.is_loaded})")

    @property
    def is_model_loaded(self) -> bool:
        """모델이 로드되어 있는지 여부."""
        return self._model is not None and self._model.is_loaded

    @property
    def tool_schema(self) -> Dict[str, Any]:
        """MCP Tool 스키마 반환."""
        return {
            "name": "exaone_generate",
            "description": "Exaone 모델을 사용하여 메시지 리스트를 받아 응답을 생성합니다.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "messages": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "role": {
                                    "type": "string",
                                    "enum": ["user", "assistant", "system"],
                                    "description": "메시지 역할",
                                },
                                "content": {
                                    "type": "string",
                                    "description": "메시지 내용",
                                },
                            },
                            "required": ["role", "content"],
                        },
                        "description": "대화 메시지 리스트",
                    },
                },
                "required": ["messages"],
            },
        }
