"""Query complexity classifier for choosing between LangChain and LangGraph."""

from typing import Literal


def classify_query_complexity(user_message: str) -> Literal["simple", "complex"]:
    """질문의 복잡도를 분류하여 랭체인 또는 랭그래프 사용 여부를 결정.
    
    Args:
        user_message: 사용자 질문 메시지
        
    Returns:
        "simple": 단답형/확실한 질문 → 랭체인 사용
        "complex": 복잡한/분기 많은 질문 → 랭그래프 사용
    """
    if not user_message or not user_message.strip():
        return "simple"
    
    message_lower = user_message.lower()
    
    # 1) 명시적 복잡 키워드 체크
    complex_keywords = [
        "비교", "compare", "차이", "장단점", "pros and cons", "pros and",
        "추천", "recommend", "어떤게 좋", "어떤 게 좋", "best", "better",
        "어떻게", "how to", "방법", "step", "단계", "절차",
        "분석", "analyze", "평가", "assess", "evaluate",
        "여러", "multiple", "모두", "all", "각각", "각",
        "vs", "versus", "대비", "대조",
        "그리고", "또한", "그런데", "하지만", "and then", "but also",
        "만약", "if", "경우", "when", "어떤 상황",
        "왜", "why", "이유", "reason",
    ]
    
    for keyword in complex_keywords:
        if keyword in message_lower:
            return "complex"
    
    # 2) 길이 체크 (긴 질문은 복잡할 가능성 높음)
    if len(user_message) > 150:
        return "complex"
    
    # 3) 복수 질문 체크 (?, ?, 또는 여러 문장)
    question_marks = user_message.count("?") + user_message.count("？") + user_message.count(".")
    if question_marks > 2:  # 여러 문장/질문
        return "complex"
    
    # 4) 번호나 리스트 형태 (1. 2. 3. 또는 - - -)
    if any(marker in user_message for marker in ["1.", "2.", "3.", "- ", "• ", "* "]):
        return "complex"
    
    # 5) 접속사로 연결된 복합 질문
    complex_conjunctions = [
        "그리고", "또한", "그런데", "하지만", "그러나",
        "and then", "but also", "in addition", "however",
        "또", "그리고", "또한", "또는", "or"
    ]
    conjunction_count = sum(1 for conj in complex_conjunctions if conj in message_lower)
    if conjunction_count >= 2:  # 여러 접속사 사용
        return "complex"
    
    # 6) 명령형 복합 동사 (예: "비교하고 추천해줘", "분석하고 설명해줘")
    action_pairs = [
        ("비교", "추천"), ("compare", "recommend"),
        ("분석", "설명"), ("analyze", "explain"),
        ("평가", "제안"), ("evaluate", "suggest"),
    ]
    for action1, action2 in action_pairs:
        if action1 in message_lower and action2 in message_lower:
            return "complex"
    
    # 기본값: 단순 질문
    return "simple"
