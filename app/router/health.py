"""Health check endpoint."""

from fastapi import APIRouter, Request

from app.schemas import HealthResponse

router = APIRouter(tags=["health"])


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
    from app.models.base import BaseLLMModel
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
