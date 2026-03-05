"""User 서비스 - 규칙 기반 사용자 요청 처리

명확한 규칙이 있는 경우 규칙 기반으로 처리합니다.
"""

from typing import Dict, Any, Optional
import re


class UserService:
    """규칙 기반 사용자 서비스"""

    def __init__(self):
        """서비스 초기화"""
        # 규칙 패턴 정의
        self.rules = {
            "greeting": {
                "patterns": [
                    r"안녕",
                    r"하이",
                    r"hello",
                    r"hi",
                ],
                "response": "안녕하세요! KOICA 프로젝트 관리 시스템입니다. 무엇을 도와드릴까요?",
            },
            "status": {
                "patterns": [
                    r"상태",
                    r"현황",
                    r"status",
                ],
                "response": "시스템 상태를 확인 중입니다. 잠시만 기다려주세요.",
            },
            "help": {
                "patterns": [
                    r"도움말",
                    r"도와줘",
                    r"help",
                    r"사용법",
                ],
                "response": "다음 기능을 사용할 수 있습니다:\n"
                "- 프로젝트 조회\n"
                "- 보고서 생성\n"
                "- 입찰서류 관리\n"
                "- ODA 용어사전 검색",
            },
            "project": {
                "patterns": [
                    r"프로젝트",
                    r"project",
                ],
                "response": "프로젝트 관련 기능입니다. 구체적으로 어떤 작업을 원하시나요?",
            },
        }

    def process(self, message: str, user_id: Optional[int] = None, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """규칙 기반으로 메시지 처리

        Args:
            message: 사용자 메시지
            user_id: 사용자 ID (선택)
            context: 추가 컨텍스트 (선택)

        Returns:
            {
                "response": str,  # 응답 메시지
                "matched_rule": str,  # 매칭된 규칙 이름
                "confidence": float,  # 규칙 매칭 신뢰도 (0.0 ~ 1.0)
            }
        """
        message_lower = message.lower().strip()

        # 규칙 매칭 시도
        best_match = None
        best_confidence = 0.0

        for rule_name, rule_data in self.rules.items():
            for pattern in rule_data["patterns"]:
                if re.search(pattern, message_lower, re.IGNORECASE):
                    # 패턴 매칭 성공
                    confidence = 0.8  # 규칙 기반은 높은 신뢰도
                    if confidence > best_confidence:
                        best_match = rule_name
                        best_confidence = confidence
                        break

        if best_match:
            # 규칙 매칭 성공
            response = self.rules[best_match]["response"]
            print(f"📋 [규칙 기반] 규칙 매칭: {best_match} (신뢰도: {best_confidence:.2f})")
            return {
                "response": response,
                "matched_rule": best_match,
                "confidence": best_confidence,
            }
        else:
            # 규칙 매칭 실패 - 규칙 기반으로 처리 불가
            print(f"⚠️  [규칙 기반] 매칭되는 규칙 없음: {message[:50]}")
            return {
                "response": None,  # None이면 규칙 기반으로 처리 불가
                "matched_rule": None,
                "confidence": 0.0,
            }

    def is_applicable(self, message: str) -> bool:
        """규칙 기반 처리 가능 여부 확인

        Args:
            message: 사용자 메시지

        Returns:
            규칙 기반으로 처리 가능하면 True
        """
        result = self.process(message)
        return result["matched_rule"] is not None
