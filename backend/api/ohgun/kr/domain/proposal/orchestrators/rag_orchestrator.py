"""LangGraph-based RAG chat workflow with local Exaone model support."""

from typing import TypedDict, Annotated, Optional, Union
import psycopg2

from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

from core.embeddings import generate_embeddings
from core.vectorstore import query_similar_documents
from artifacts.models.interfaces.base import BaseLLMModel

# Gemini는 선택적 지원 (fallback)
try:
    from langchain_google_genai import ChatGoogleGenerativeAI
except ImportError:
    ChatGoogleGenerativeAI = None  # type: ignore

# -------------------------
# 1) State 정의
# -------------------------
class AgentState(TypedDict):
    """LangGraph 상태 정의."""
    # messages: 대화 로그(누적)
    messages: Annotated[list, add_messages]
    # rag_context: RAG 검색 결과 (선택적)
    rag_context: Optional[str]
    # db_connection: 데이터베이스 연결 (상태에 포함하지 않음, 노드에서 받음)
    # embedding_dimension: 임베딩 차원 (상태에 포함하지 않음, 노드에서 받음)


# Note: Tool 기능은 제거했습니다. Exaone 모델은 Tool을 지원하지 않으므로
# RAG 검색은 별도의 노드로 처리합니다.


# -------------------------
# 3) RAG 검색 노드
# -------------------------
def rag_search_node(
    state: AgentState,
    db_conn: psycopg2.extensions.connection,
    embedding_dim: int
):
    """RAG 검색을 수행하고 컨텍스트를 상태에 추가.

    Args:
        state: 현재 상태
        db_conn: 데이터베이스 연결
        embedding_dim: 임베딩 차원

    Returns:
        업데이트된 상태
    """
    # 마지막 사용자 메시지 가져오기
    user_messages = [msg for msg in state["messages"] if isinstance(msg, HumanMessage)]
    if not user_messages:
        return {"rag_context": None}

    last_user_msg = user_messages[-1]
    query = last_user_msg.content if hasattr(last_user_msg, 'content') else str(last_user_msg)

    print(f"🔍 [LangGraph] RAG 검색 노드 실행: {query[:50]}...")

    try:
        # Generate embedding for query
        query_embeddings = generate_embeddings([query], embedding_dim)
        query_vector = query_embeddings[0]

        # Search for similar documents
        similar_docs = query_similar_documents(db_conn, query_vector, limit=3)

        if similar_docs:
            context = "\n\n".join([content for _, content, _ in similar_docs])
            print(f"📚 [LangGraph] {len(similar_docs)}개 관련 문서 검색 완료")
            return {"rag_context": context}
        else:
            print(f"⚠️ [LangGraph] 관련 문서를 찾지 못했습니다")
            return {"rag_context": None}
    except Exception as e:
        print(f"⚠️ [LangGraph] RAG 검색 오류: {str(e)[:200]}")
        return {"rag_context": None}


# -------------------------
# 4) Model 노드
# -------------------------
def create_model_node(
    chat_model: Optional[Union[BaseLLMModel, ChatGoogleGenerativeAI]],
    db_conn: psycopg2.extensions.connection,
    embedding_dim: int
):
    """Model 노드 생성 (동적 생성).

    Args:
        chat_model: 채팅 모델 (Exaone 또는 Gemini, 기본은 Exaone)
        db_conn: 데이터베이스 연결
        embedding_dim: 임베딩 차원

    Returns:
        Model 노드 함수
    """
    # Check if it's a BaseLLMModel (Exaone) or Gemini model
    is_base_model = isinstance(chat_model, BaseLLMModel)

    def model_node(state: AgentState):
        """Model 노드: LLM을 호출하여 응답 생성."""
        if chat_model is None:
            return {
                "messages": [
                    AIMessage(content="⚠️ 채팅 모델을 사용할 수 없습니다.")
                ]
            }

        # RAG 컨텍스트 가져오기
        rag_context = state.get("rag_context")
        print(f"🤖 [LangGraph] Model 노드 실행 (RAG 컨텍스트: {'있음' if rag_context else '없음'})")

        # Prepare messages
        if is_base_model:
            # BaseLLMModel (Exaone) - use list format
            messages_list = []

            # System message with RAG context
            if rag_context:
                system_content = f"""당신은 친절한 AI 어시스턴트입니다. 아래 정보를 바탕으로 사용자의 질문에 자연스럽고 대화하듯이 답변해주세요. 정보를 나열하지 말고 자신의 말로 쉽게 설명하세요.

참고 정보:
{rag_context}"""
            else:
                system_content = "당신은 친절한 AI 어시스턴트입니다. 사용자의 질문에 자연스럽고 대화하듯이 답변해주세요."

            messages_list.append({"role": "system", "content": system_content})

            # User messages
            for msg in state["messages"]:
                if isinstance(msg, HumanMessage):
                    messages_list.append({"role": "user", "content": msg.content})
                elif isinstance(msg, AIMessage):
                    messages_list.append({"role": "assistant", "content": msg.content})

            # Get response
            try:
                response_text = chat_model.invoke(messages_list)
                return {"messages": [AIMessage(content=response_text)]}
            except Exception as e:
                error_msg = str(e)[:200]
                return {
                    "messages": [
                        AIMessage(content=f"⚠️ 응답 생성 중 오류: {error_msg}")
                    ]
                }
        else:
            # Gemini model - use LangChain messages
            messages = []

            # System message with RAG context
            if rag_context:
                system_content = f"""당신은 친절하고 도움이 되는 AI 어시스턴트입니다.

다음은 사용자의 질문과 관련된 참고 정보입니다:

{rag_context}

**중요 지시사항:**
1. 위 정보를 바탕으로 사용자의 질문에 자연스럽고 대화하듯이 답변하세요.
2. 정보를 불릿 포인트나 번호로 나열하지 말고, 자신의 말로 쉽고 이해하기 쉽게 풀어서 설명하세요.
3. 친절하고 자연스러운 톤으로 대화하듯이 답변하세요.
4. 참고 정보에 없는 내용이 필요하면 일반적인 지식을 바탕으로 보완할 수 있습니다.
5. "참고 문서", "참고 정보" 같은 표현을 사용하지 말고, 자연스럽게 정보를 통합하여 답변하세요."""
            else:
                system_content = """당신은 친절하고 도움이 되는 AI 어시스턴트입니다. 사용자의 질문에 자연스럽고 대화하듯이 답변하세요."""

            messages.append(SystemMessage(content=system_content))

            # Add conversation history
            for msg in state["messages"]:
                if isinstance(msg, (HumanMessage, AIMessage)):
                    messages.append(msg)

            # Gemini 모델 호출 (Tool 없이)
            try:
                resp = chat_model.invoke(messages)

                # Handle response
                if hasattr(resp, 'content'):
                    return {"messages": [AIMessage(content=resp.content)]}
                else:
                    return {"messages": [AIMessage(content=str(resp))]}
            except Exception as e:
                error_msg = str(e)[:200]
                return {
                    "messages": [
                        AIMessage(content=f"⚠️ 응답 생성 중 오류: {error_msg}")
                    ]
                }

    return model_node


# Note: Tool 노드와 조건 분기는 제거했습니다.
# Exaone 모델은 Tool을 지원하지 않으므로 RAG 검색은 별도 노드로 처리합니다.


# -------------------------
# 7) Graph 빌드
# -------------------------
def build_rag_graph(
    chat_model: Optional[Union[BaseLLMModel, ChatGoogleGenerativeAI]],
    db_conn: psycopg2.extensions.connection,
    embedding_dim: int
):
    """RAG 기반 LangGraph 빌드 (로컬 Exaone 모델 우선 사용).

    Args:
        chat_model: 채팅 모델 (기본: Exaone, fallback: Gemini)
        db_conn: 데이터베이스 연결
        embedding_dim: 임베딩 차원

    Returns:
        컴파일된 그래프
    """
    g = StateGraph(AgentState)

    # 노드 추가
    g.add_node("rag_search", lambda state: rag_search_node(state, db_conn, embedding_dim))
    g.add_node("model", create_model_node(chat_model, db_conn, embedding_dim))

    # 엔트리 포인트: RAG 검색부터 시작
    g.set_entry_point("rag_search")

    # RAG 검색 후 모델로 이동, 모델 후 바로 종료
    # (Exaone 모델은 Tool을 지원하지 않으므로 단순한 흐름)
    g.add_edge("rag_search", "model")
    g.add_edge("model", END)

    return g.compile()


# -------------------------
# 8) 간단 실행 헬퍼
# -------------------------
def run_rag_chat(
    user_text: str,
    chat_model: Optional[Union[BaseLLMModel, ChatGoogleGenerativeAI]],
    db_conn: psycopg2.extensions.connection,
    embedding_dim: int,
    system_prompt: Optional[str] = None
) -> str:
    """RAG 기반 채팅 실행.

    Args:
        user_text: 사용자 입력 텍스트
        chat_model: 채팅 모델
        db_conn: 데이터베이스 연결
        embedding_dim: 임베딩 차원
        system_prompt: 시스템 프롬프트 (선택적)

    Returns:
        AI 응답 텍스트
    """
    # Graph 빌드
    graph = build_rag_graph(chat_model, db_conn, embedding_dim)

    # 초기 상태 설정
    messages = []
    if system_prompt:
        messages.append(SystemMessage(content=system_prompt))
    messages.append(HumanMessage(content=user_text))

    init_state: AgentState = {
        "messages": messages,
        "rag_context": None
    }

    # Graph 실행
    try:
        out = graph.invoke(init_state)
        # 마지막 AIMessage의 content 반환
        last_message = out["messages"][-1]
        if hasattr(last_message, 'content'):
            return last_message.content
        else:
            return str(last_message)
    except Exception as e:
        error_msg = str(e)[:200]
        return f"⚠️ 그래프 실행 중 오류: {error_msg}"
