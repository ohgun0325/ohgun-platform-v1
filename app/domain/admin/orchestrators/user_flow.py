"""User Flow - 사용자 요청 처리 오케스트레이터

규칙 기반과 정책 기반을 자동으로 분기하여 처리합니다.
"""

from typing import Dict, Any, Optional, TYPE_CHECKING

from app.domain.admin.services.user_service import UserService
from app.domain.admin.agents.user_agent import UserAgent

if TYPE_CHECKING:
    from artifacts.models.interfaces.base import BaseLLMModel


class UserFlow:
    """사용자 요청 처리 오케스트레이터

    규칙 기반과 정책 기반을 자동으로 분기:
    - 규칙 기반: 명확한 규칙이 있는 경우 (인사, 도움말 등)
    - 정책 기반: 복잡한 요청의 경우 (Fine-tuned 모델 사용)
    """

    def __init__(
        self,
        base_model: Optional["BaseLLMModel"] = None,
        adapter_name: Optional[str] = None,
    ):
        """UserFlow 초기화

        Args:
            base_model: 정책 기반 처리에 사용할 기본 모델 (None이면 Gemini 사용)
            adapter_name: Fine-tuned 어댑터 이름 (선택)
        """
        self.rule_service = UserService()
        self.policy_agent = UserAgent(base_model=base_model, adapter_name=adapter_name)

    def process(
        self,
        message: str,
        user_id: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """사용자 요청 처리 (규칙/정책 자동 분기)

        처리 흐름:
        1. 규칙 기반 서비스로 처리 가능 여부 확인
        2. 규칙 기반으로 처리 가능하면 규칙 기반 사용
        3. 규칙 기반으로 처리 불가능하면 정책 기반 사용

        Args:
            message: 사용자 메시지
            user_id: 사용자 ID (선택)
            context: 추가 컨텍스트 (선택)

        Returns:
            {
                "response": str,  # 응답 메시지
                "method": str,  # "rule-based" 또는 "policy-based"
                "sources": list[str],  # 참고 문서 (선택)
            }
        """
        print(f"🔄 [UserFlow] 요청 처리 시작: {message[:50]}...")

        # 1단계: 규칙 기반 처리 시도
        rule_result = self.rule_service.process(message, user_id, context)

        if rule_result["matched_rule"] is not None:
            # 규칙 기반으로 처리 가능
            print(f"✅ [UserFlow] 규칙 기반 처리 선택 (규칙: {rule_result['matched_rule']})")
            return {
                "response": rule_result["response"],
                "method": "rule-based",
                "sources": [],
            }

        # 2단계: 규칙 기반으로 처리 불가능 → 정책 기반 사용
        print(f"🔄 [UserFlow] 규칙 기반 처리 불가 → 정책 기반 처리로 전환")
        policy_result = self.policy_agent.process(message, user_id, context)

        return {
            "response": policy_result["response"],
            "method": policy_result["method"],
            "sources": policy_result.get("sources", []),
        }

    def get_available_adapters(self) -> list[str]:
        """사용 가능한 Fine-tuned 어댑터 목록 반환

        Returns:
            어댑터 이름 목록
        """
        # 하이픈이 있는 폴더명은 직접 import 불가하므로 importlib 사용
        import importlib.util
        from pathlib import Path
        adapters_path = Path(__file__).parent.parent.parent.parent / "artifacts" / "fine-tuned-adapters" / "__init__.py"
        if adapters_path.exists():
            spec = importlib.util.spec_from_file_location("fine_tuned_adapters", adapters_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            get_adapter_loader = module.get_adapter_loader
        else:
            get_adapter_loader = None

        if get_adapter_loader:
            adapter_loader = get_adapter_loader()
            if adapter_loader:
                return adapter_loader.list_adapters()
        return []
