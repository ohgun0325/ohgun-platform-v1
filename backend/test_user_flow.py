"""User Flow 테스트 스크립트

규칙 기반 및 정책 기반 분기 로직을 테스트합니다.
"""

import sys
from pathlib import Path

# kr 모듈 루트를 Python 경로에 추가 (domain 등 import 해결용)
project_root = Path(__file__).parent.absolute()
kr_root = project_root / "api" / "ohgun" / "kr"
if str(kr_root) not in sys.path:
    sys.path.insert(0, str(kr_root))

from domain.admin.orchestrators.user_flow import UserFlow
from domain.admin.services.user_service import UserService
from domain.admin.agents.user_agent import UserAgent


def test_rule_based_service():
    """규칙 기반 서비스 테스트"""
    print("=" * 60)
    print("🧪 규칙 기반 서비스 테스트")
    print("=" * 60)

    service = UserService()

    test_cases = [
        "안녕하세요",
        "하이",
        "도움말",
        "프로젝트 상태",
        "복잡한 프로젝트 관리 질문입니다",
    ]

    for message in test_cases:
        print(f"\n📝 테스트 메시지: '{message}'")
        result = service.process(message)
        if result["matched_rule"]:
            print(f"   ✅ 규칙 매칭: {result['matched_rule']}")
            print(f"   📋 응답: {result['response'][:50]}...")
            print(f"   📊 신뢰도: {result['confidence']:.2f}")
        else:
            print(f"   ❌ 규칙 매칭 실패 (정책 기반으로 전환 필요)")


def test_policy_based_agent():
    """정책 기반 에이전트 테스트"""
    print("\n" + "=" * 60)
    print("🧪 정책 기반 에이전트 테스트")
    print("=" * 60)

    try:
        agent = UserAgent()
        print("\n📝 테스트 메시지: 'KOICA 프로젝트 관리 방법을 알려주세요'")
        result = agent.process("KOICA 프로젝트 관리 방법을 알려주세요")
        print(f"   ✅ 처리 완료")
        print(f"   📋 응답: {result['response'][:100]}...")
        print(f"   📊 방법: {result['method']}")
        print(f"   📊 신뢰도: {result['confidence']:.2f}")
    except Exception as e:
        print(f"   ❌ 오류 발생: {str(e)}")
        print("   (Gemini API 키가 설정되지 않았거나 모델 로드 실패)")


def test_user_flow():
    """UserFlow 통합 테스트"""
    print("\n" + "=" * 60)
    print("🧪 UserFlow 통합 테스트 (규칙/정책 자동 분기)")
    print("=" * 60)

    flow = UserFlow()

    test_cases = [
        {
            "message": "안녕하세요",
            "expected_method": "rule-based",
        },
        {
            "message": "도움말",
            "expected_method": "rule-based",
        },
        {
            "message": "KOICA 프로젝트의 진행 상황과 예산 사용 현황을 상세히 분석해주세요",
            "expected_method": "policy-based",
        },
        {
            "message": "프로젝트",
            "expected_method": "rule-based",
        },
    ]

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n[테스트 {i}] 메시지: '{test_case['message']}'")
        print(f"   예상 방법: {test_case['expected_method']}")

        try:
            result = flow.process(test_case["message"])
            actual_method = result["method"]
            print(f"   ✅ 실제 방법: {actual_method}")

            if actual_method == test_case["expected_method"]:
                print(f"   ✅ 예상과 일치!")
            else:
                print(f"   ⚠️  예상과 다름 (예상: {test_case['expected_method']}, 실제: {actual_method})")

            print(f"   📋 응답: {result['response'][:80]}...")

        except Exception as e:
            print(f"   ❌ 오류 발생: {str(e)}")


def test_api_endpoint():
    """API 엔드포인트 테스트 (서버 실행 필요)"""
    print("\n" + "=" * 60)
    print("🧪 API 엔드포인트 테스트")
    print("=" * 60)
    print("\n⚠️  이 테스트는 FastAPI 서버가 실행 중이어야 합니다.")
    print("   서버 실행: python app/main.py")
    print("\n다음 명령으로 테스트하세요:")
    print("\n1. 규칙 기반 테스트:")
    print('   curl -X POST "http://localhost:8000/api/v1/admin/user" \\')
    print('        -H "Content-Type: application/json" \\')
    print('        -d \'{"message": "안녕하세요"}\'')
    print("\n2. 정책 기반 테스트:")
    print('   curl -X POST "http://localhost:8000/api/v1/admin/user" \\')
    print('        -H "Content-Type: application/json" \\')
    print('        -d \'{"message": "KOICA 프로젝트 관리 방법을 알려주세요"}\'')


if __name__ == "__main__":
    print("🚀 User Flow 테스트 시작\n")

    # 1. 규칙 기반 서비스 테스트
    test_rule_based_service()

    # 2. 정책 기반 에이전트 테스트 (선택적 - Gemini API 필요)
    # test_policy_based_agent()

    # 3. UserFlow 통합 테스트
    test_user_flow()

    # 4. API 엔드포인트 테스트 안내
    test_api_endpoint()

    print("\n" + "=" * 60)
    print("✅ 테스트 완료!")
    print("=" * 60)
