"""KOICA MCP 서버 사용 예시.

KoElectra와 Exaone을 FastMCP로 연결하여 사용하는 방법을 보여줍니다.
"""

from app.domain.koica.mcp.server import create_mcp_server
from app.domain.koica.services.policy_rule_classifier import PolicyRuleClassifier
from artifacts.models.core.manager import ModelManager


def example_mcp_pipeline():
    """MCP 파이프라인 사용 예시."""
    print("=" * 60)
    print("KOICA MCP 서버 예시")
    print("=" * 60)

    # 1) KoElectra 분류기 초기화
    classifier = PolicyRuleClassifier()
    if not classifier.is_available():
        classifier.load()

    # 2) Exaone 모델 로드
    model_manager = ModelManager()
    exaone_model = model_manager.get_chat_model("exaone-2.4b")

    if exaone_model is None or not exaone_model.is_loaded:
        print("⚠️ Exaone 모델을 로드할 수 없습니다.")
        return

    # 3) MCP 서버 생성
    mcp_server = create_mcp_server(
        koelectra_classifier=classifier,
        exaone_model=exaone_model,
    )

    print("✅ MCP 서버 생성 완료")

    # 4) 파이프라인 Tool 사용 (KoElectra → Exaone)
    question = "KOICA 사업 절차는?"
    result = mcp_server._classify_and_generate(
        question=question,
        system_prompt="당신은 KOICA 업무를 돕는 친절한 AI 어시스턴트입니다.",
    )

    print("\n" + "=" * 60)
    print("파이프라인 결과:")
    print("=" * 60)
    print(f"질문: {question}")
    print(f"분류: {result['classification']}")
    print(f"응답: {result.get('response', '')[:200]}...")
    if result.get("error"):
        print(f"오류: {result['error']}")

    # 5) 개별 Tool 사용 예시
    print("\n" + "=" * 60)
    print("개별 Tool 사용:")
    print("=" * 60)

    # KoElectra만 사용
    classification = mcp_server._classify_with_koelectra("10억이라는 금액 이상은 차단해야 한다.")
    print(f"KoElectra 분류: {classification}")

    # Exaone만 사용
    exaone_result = mcp_server._generate_with_exaone([
        {"role": "system", "content": "당신은 KOICA 업무를 돕는 친절한 AI 어시스턴트입니다."},
        {"role": "user", "content": "ODA란 무엇인가요?"},
    ])
    print(f"Exaone 응답: {exaone_result.get('response', '')[:200]}...")


if __name__ == "__main__":
    example_mcp_pipeline()
