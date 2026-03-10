"""User 에이전트 - 정책 기반 사용자 요청 처리

복잡한 요청은 Fine-tuned 모델을 사용하여 정책 기반으로 처리합니다.
"""

from typing import Dict, Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from artifacts.models.interfaces.base import BaseLLMModel
    from langchain_google_genai import ChatGoogleGenerativeAI

# 하이픈이 있는 폴더명은 직접 import 불가하므로 importlib 사용
import importlib.util
from pathlib import Path

def _load_adapter_module():
    """어댑터 모듈 동적 로드"""
    adapters_path = Path(__file__).parent.parent.parent.parent / "artifacts" / "fine-tuned-adapters" / "__init__.py"
    if adapters_path.exists():
        spec = importlib.util.spec_from_file_location("fine_tuned_adapters", adapters_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    return None

_adapter_module = _load_adapter_module()
get_adapter_loader = _adapter_module.get_adapter_loader if _adapter_module else None
from artifacts.models.interfaces.base import BaseLLMModel

try:
    from langchain_google_genai import ChatGoogleGenerativeAI
except ImportError:
    ChatGoogleGenerativeAI = None  # type: ignore


class UserAgent:
    """정책 기반 사용자 에이전트"""

    def __init__(
        self,
        base_model: Optional["BaseLLMModel"] = None,
        adapter_name: Optional[str] = None,
    ):
        """에이전트 초기화

        Args:
            base_model: 기본 모델 (None이면 Gemini 사용)
            adapter_name: Fine-tuned 어댑터 이름 (선택)
        """
        self.base_model = base_model
        self.adapter_name = adapter_name
        self._adapter = None
        self._model = None

    def _load_model(self):
        """모델 및 어댑터 로드 (lazy loading)"""
        if self._model is not None:
            return

        # Fine-tuned 어댑터가 있으면 로드
        if self.adapter_name and self.base_model and get_adapter_loader:
            adapter_loader = get_adapter_loader()
            if adapter_loader:
                adapter = adapter_loader.load_adapter(
                    self.adapter_name,
                    base_model=self.base_model,
                )
                if adapter:
                    self._adapter = adapter
                    self._model = adapter
                    print(f"✅ [정책 기반] Fine-tuned 어댑터 로드: {self.adapter_name}")
                    return

        # 어댑터가 없으면 base model 사용
        if self.base_model:
            self._model = self.base_model
            print("✅ [정책 기반] Base 모델 사용")
            return

        # Fallback: Gemini 사용
        if ChatGoogleGenerativeAI:
            try:
                from app.core.llm.gemini import get_chat_model

                self._model = get_chat_model()
                print("✅ [정책 기반] Gemini 모델 사용 (Fallback)")
            except Exception as e:
                print(f"⚠️  [정책 기반] Gemini 로드 실패: {str(e)}")

    def process(
        self,
        message: str,
        user_id: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """정책 기반으로 메시지 처리

        Args:
            message: 사용자 메시지
            user_id: 사용자 ID (선택)
            context: 추가 컨텍스트 (선택)

        Returns:
            {
                "response": str,  # 응답 메시지
                "method": str,  # "policy-based"
                "confidence": float,  # 처리 신뢰도
            }
        """
        # 모델 로드
        self._load_model()

        if self._model is None:
            raise ValueError("사용 가능한 모델이 없습니다.")

        # 시스템 프롬프트 구성
        system_prompt = self._build_system_prompt(user_id, context)

        # 메시지 처리
        try:
            if isinstance(self._model, BaseLLMModel):
                # Exaone 같은 로컬 모델
                response = self._model.generate(
                    prompt=system_prompt + "\n\n사용자: " + message + "\n\n어시스턴트:"
                )
            elif ChatGoogleGenerativeAI and isinstance(self._model, ChatGoogleGenerativeAI):
                # Gemini 모델
                from langchain_core.messages import HumanMessage, SystemMessage

                messages = [
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=message),
                ]
                response_obj = self._model.invoke(messages)
                response = (
                    response_obj.content
                    if hasattr(response_obj, "content")
                    else str(response_obj)
                )
            else:
                raise ValueError(f"지원하지 않는 모델 타입: {type(self._model)}")

            print(f"✅ [정책 기반] 응답 생성 완료 (길이: {len(response)}자)")

            return {
                "response": response,
                "method": "policy-based",
                "confidence": 0.7,  # 정책 기반은 중간 신뢰도
            }

        except Exception as e:
            error_msg = str(e)
            print(f"❌ [정책 기반] 처리 오류: {error_msg}")
            raise

    def _build_system_prompt(
        self, user_id: Optional[int] = None, context: Optional[Dict[str, Any]] = None
    ) -> str:
        """시스템 프롬프트 구성

        Args:
            user_id: 사용자 ID
            context: 추가 컨텍스트

        Returns:
            시스템 프롬프트 문자열
        """
        prompt = """당신은 KOICA(한국국제협력단) 프로젝트 관리 시스템의 AI 어시스턴트입니다.

주요 역할:
1. 프로젝트 관리 및 조회 지원
2. 보고서 생성 지원
3. 입찰서류 관리 지원
4. ODA 용어사전 검색 지원
5. 사용자 질문에 대한 정확하고 도움이 되는 답변 제공

답변 시 주의사항:
- 정확하고 명확한 정보 제공
- KOICA의 업무 프로세스에 맞는 답변
- 필요시 관련 문서나 데이터 참조 제안
"""

        if user_id:
            prompt += f"\n현재 사용자 ID: {user_id}"

        if context:
            prompt += f"\n추가 컨텍스트: {context}"

        return prompt

    def unload(self) -> None:
        """모델 및 어댑터 언로드 (메모리 해제)"""
        if self._adapter and hasattr(self._adapter, "unload"):
            self._adapter.unload()
        self._model = None
        self._adapter = None
        print("🗑️  [정책 기반] 모델 언로드 완료")
