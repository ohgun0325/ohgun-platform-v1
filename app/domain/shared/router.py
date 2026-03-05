"""공통 라우터 - Health check 및 Search 기능"""

from fastapi import APIRouter, HTTPException, Request

from app.core.embeddings import generate_embeddings
from app.core.vectorstore import query_similar_documents
from app.schemas import (
    HealthResponse,
    SearchRequest,
    SearchResponse,
    SearchResult,
)

router = APIRouter(tags=["health", "search"])


@router.get("/health", response_model=HealthResponse)
async def health_check(request: Request) -> HealthResponse:
    """Health check endpoint.

    Returns:
        Health status information including database and Gemini API status.
    """
    db_conn = request.app.state.db_connection
    embedding_dim = request.app.state.embedding_dimension
    chat_model = getattr(request.app.state, "chat_model", None)  # QLoRA 사용 시 없을 수 있음
    qlora_service = getattr(request.app.state, "qlora_service", None)  # QLoRA 서비스 확인

    # Check model type
    from artifacts.models.interfaces.base import BaseLLMModel
    model_type = None
    if qlora_service and qlora_service.is_loaded:
        model_type = "QLoRA"
    elif chat_model:
        if isinstance(chat_model, BaseLLMModel):
            model_type = "Exaone"
        else:
            model_type = "Gemini"

    return HealthResponse(
        status="healthy",
        database="connected" if db_conn else "disconnected",
        embedding_dimension=embedding_dim,
        gemini_available=chat_model is not None and model_type == "Gemini",
        model_type=model_type,
    )


@router.post("/search", response_model=SearchResponse)
async def search(request: Request, search_request: SearchRequest) -> SearchResponse:
    """Search similar documents.

    Args:
        request: FastAPI request object.
        search_request: Search request with query and limit.

    Returns:
        Search results with similar documents.

    Raises:
        HTTPException: If database is not connected or other errors occur.
    """
    db_conn = request.app.state.db_connection
    embedding_dim = request.app.state.embedding_dimension

    if not db_conn:
        raise HTTPException(status_code=503, detail="데이터베이스 연결 없음")

    if not search_request.query.strip():
        raise HTTPException(status_code=400, detail="검색어가 비어있습니다")

    try:
        # Generate embedding for query
        query_embeddings = generate_embeddings([search_request.query], embedding_dim)

        # Search similar documents
        similar_docs = query_similar_documents(
            db_conn,
            query_embeddings[0],
            limit=search_request.limit
        )

        results = [
            SearchResult(id=doc_id, content=content, distance=float(distance))
            for doc_id, content, distance in similar_docs
        ]

        return SearchResponse(results=results)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"오류 발생: {str(e)}")
