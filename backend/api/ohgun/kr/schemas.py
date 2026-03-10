"""Pydantic models for request/response schemas."""

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Chat request model."""

    message: str = Field(..., min_length=1, description="User's message")


class ChatResponse(BaseModel):
    """Chat response model."""

    response: str = Field(..., description="AI's response")
    sources: list[str] = Field(default_factory=list, description="Source documents")


class SearchRequest(BaseModel):
    """Search request model."""

    query: str = Field(..., min_length=1, description="Search query")
    limit: int = Field(default=3, ge=1, le=10, description="Number of results")


class SearchResult(BaseModel):
    """Individual search result."""

    id: int = Field(..., description="Document ID")
    content: str = Field(..., description="Document content")
    distance: float = Field(..., description="Cosine distance")


class SearchResponse(BaseModel):
    """Search response model."""

    results: list[SearchResult] = Field(default_factory=list)


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(..., description="Service status")
    database: str = Field(..., description="Database connection status")
    embedding_dimension: int = Field(..., description="Current embedding dimension")
    gemini_available: bool = Field(..., description="Gemini API availability")
    model_type: str | None = Field(default=None, description="Current chat model type (Exaone or Gemini)")

