"""Chat router for RAG-based conversation with QLoRA, LangChain, and LangGraph."""

import asyncio
from fastapi import APIRouter, HTTPException, Request

from core.embeddings import generate_embeddings
from core.vectorstore import query_similar_documents
from core.query_classifier import classify_query_complexity
from schemas import ChatRequest, ChatResponse
from langchain_core.messages import HumanMessage, SystemMessage

router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(request: Request, chat_request: ChatRequest) -> ChatResponse:
    """Chat with AI using RAG and QLoRA model.

    Args:
        request: FastAPI request object.
        chat_request: Chat request with user message.

    Returns:
        AI response with source documents.

    Raises:
        HTTPException: If database is not connected or other errors occur.
    """
    db_conn = request.app.state.db_connection
    embedding_dim = request.app.state.embedding_dimension
    qlora_service = getattr(request.app.state, "qlora_service", None)

    if not db_conn:
        raise HTTPException(status_code=503, detail="데이터베이스 연결 없음")

    if not chat_request.message.strip():
        raise HTTPException(status_code=400, detail="메시지가 비어있습니다")

    try:
        # RAG: Get similar documents for context
        # generate_embeddings는 스레드 안전하지만, DB 연결은 스레드 안전하지 않음
        # 따라서 DB 쿼리는 동기로 실행하되, 연결 상태를 확인
        query_embeddings = await asyncio.to_thread(
            generate_embeddings,
            [chat_request.message],
            embedding_dim
        )
        # DB 연결은 스레드 안전하지 않으므로 주의
        # query_similar_documents 내부에서 연결 상태를 확인하고 재연결함
        similar_docs = await asyncio.to_thread(
            query_similar_documents,
            db_conn,
            query_embeddings[0],
            3  # limit
        )

        sources = [content for _, content, _ in similar_docs]

        # Use QLoRA service if available
        if qlora_service and qlora_service.is_loaded:
            # Prepare context from RAG results
            context = "\n\n".join(sources) if sources else ""

            # Format message with context for QLoRA model
            if context:
                formatted_message = f"""다음은 참고할 수 있는 정보입니다:

{context}

위 정보를 바탕으로 다음 질문에 답변해주세요:

{chat_request.message}"""
            else:
                formatted_message = chat_request.message

            # Get response from QLoRA model (동기 함수를 비동기로 실행)
            try:
                # 키워드 인자로 명시적으로 전달
                def call_qlora_chat():
                    return qlora_service.chat(
                        message=formatted_message,
                        history=None,
                        max_new_tokens=512,
                        temperature=0.7,
                        top_p=0.9,
                    )

                response = await asyncio.to_thread(call_qlora_chat)
            except RuntimeError as e:
                # 모델 관련 에러 처리
                error_msg = str(e)
                if "로드되지 않았습니다" in error_msg:
                    raise HTTPException(
                        status_code=503,
                        detail=f"QLoRA 모델 로드 오류: {error_msg}"
                    )
                raise HTTPException(
                    status_code=500,
                    detail=f"QLoRA 응답 생성 오류: {error_msg}"
                )
        else:
            # QLoRA가 없을 때: 질문 복잡도에 따라 랭체인 또는 랭그래프 선택
            chat_model = getattr(request.app.state, "chat_model", None)
            rag_graph = getattr(request.app.state, "rag_graph", None)
            
            # 1) 질문 복잡도 분류
            query_type = classify_query_complexity(chat_request.message)
            print(f"📊 Query Type: {query_type} | Message: {chat_request.message[:50]}...")
            
            if query_type == "complex" and rag_graph is not None:
                # 랭그래프 사용: 복잡한 질문
                print(f"🔄 LangGraph 사용: 복잡한 질문 처리 시작")
                try:
                    init_state = {
                        "messages": [
                            SystemMessage(content="당신은 친절한 AI 어시스턴트입니다."),
                            HumanMessage(content=chat_request.message)
                        ],
                        "rag_context": None
                    }
                    
                    print(f"🔧 LangGraph.invoke() 호출 중...")
                    out = await asyncio.to_thread(rag_graph.invoke, init_state)
                    response = out["messages"][-1].content
                    
                    # Sources 추출 (rag_context에서 또는 기존 similar_docs 사용)
                    if out.get("rag_context"):
                        # Context를 줄바꿈으로 분리하여 sources로 변환
                        context_parts = [s.strip() for s in out["rag_context"].split("\n\n") if s.strip()]
                        sources = context_parts[:3]  # 최대 3개
                        print(f"📚 LangGraph RAG Context에서 {len(sources)}개 sources 추출")
                    else:
                        # rag_context가 없으면 이미 추출한 sources 사용
                        print(f"📚 LangGraph: 기존 RAG 검색 결과 사용 ({len(sources)}개 sources)")
                    
                    print(f"✅ LangGraph 응답 생성 완료 (응답 길이: {len(response)}자)")
                except Exception as e:
                    error_msg = str(e)[:200]
                    print(f"⚠️ LangGraph 실행 오류: {error_msg}, 랭체인으로 fallback")
                    # Fallback to LangChain
                    from core.chat_chain import chat_with_ai
                    response = await asyncio.to_thread(
                        chat_with_ai,
                        db_conn,
                        chat_request.message,
                        embedding_dim,
                        chat_model
                    )
                    # Sources는 이미 위에서 추출됨
            else:
                # 랭체인 사용: 단순 질문 또는 Graph가 없는 경우
                if query_type == "simple":
                    print(f"🔄 LangChain 사용: 단순 질문 처리")
                else:
                    print(f"🔄 LangChain 사용: Graph가 없어 fallback")
                
                from core.chat_chain import chat_with_ai
                
                response = await asyncio.to_thread(
                    chat_with_ai,
                    db_conn,
                    chat_request.message,
                    embedding_dim,
                    chat_model
                )
                # Sources는 이미 위에서 추출됨
                print(f"✅ LangChain 응답 생성 완료 (응답 길이: {len(response)}자)")

        return ChatResponse(response=response, sources=sources)

    except HTTPException:
        # HTTPException은 그대로 전달
        raise
    except Exception as e:
        # 상세한 에러 정보 로깅
        import traceback
        error_detail = str(e)
        print(f"❌ Chat API 오류: {error_detail}")
        print(f"   Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"오류 발생: {error_detail[:200]}"  # 에러 메시지 길이 제한
        )
