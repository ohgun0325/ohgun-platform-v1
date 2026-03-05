"""Application configuration management."""

import os
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database configuration
    # Neon PostgreSQL 연결 정보 (환경 변수로 오버라이드 가능)
    database_url: Optional[str] = None  # 전체 URL (우선순위 높음, DATABASE_URL 환경 변수)
    postgres_host: str = "ep-blue-bonus-a1zf9qhw-pooler.ap-southeast-1.aws.neon.tech"
    postgres_port: int = 5432
    postgres_user: str = "neondb_owner"
    postgres_password: str = "npg_CgW5GmNnP0uq"
    postgres_db: str = "neondb"
    postgres_sslmode: str = "require"  # SSL 모드

    # Gemini API configuration
    gemini_api_key: Optional[str] = None
    gemini_model: str = "gemini-2.0-flash"  # 최신 Gemini 모델 (gemini-pro는 더 이상 사용 불가, gemini-1.5는 retired)
    gemini_embedding_model: str = "text-embedding-004"
    gemini_temperature: float = 0.7

    # Application settings
    app_title: str = "LangChain Chatbot API"
    app_description: str = "RAG 기반 AI 챗봇 API with Neon PostgreSQL"
    app_version: str = "1.0.0"
    debug: bool = False  # 디버그 모드 (SQL 쿼리 로깅 등)

    # CORS settings
    cors_origins: str = "*"  # 환경 변수에서 쉼표로 구분된 문자열 또는 "*"로 설정
    cors_allow_credentials: bool = True
    cors_allow_methods: list[str] = ["*"]
    cors_allow_headers: list[str] = ["*"]

    def get_cors_origins(self) -> list[str]:
        """CORS origins를 리스트로 변환"""
        if self.cors_origins == "*":
            return ["*"]
        return [origin.strip() for origin in self.cors_origins.split(",")]

    # RAG settings
    embedding_dimension: int = 3  # Default, will be updated dynamically
    similarity_search_limit: int = 3

    # Local LLM model configuration
    local_models_dir: str = "models"  # Directory where models are stored
    default_chat_model: Optional[str] = "exaone-2.4b"  # Default chat model name (Exaone)
    default_embedding_model: Optional[str] = None  # Default embedding model name
    model_device: str = "cuda"  # Device to load models on: "auto" (auto-detect GPU), "cpu", "cuda", "mps"
    model_dtype: str = "float16"  # Model data type: "float32", "float16" (faster + less memory), "bfloat16"

    # QLoRA configuration
    use_qlora: bool = True  # QLoRA 모델 사용 여부 (True면 기존 모델 대신 QLoRA 사용)
    qlora_model_name: str = "lg-ai/exaone-3.5-2.4b-instruct"  # QLoRA base model (Exaone)
    qlora_output_dir: str = "models/qlora_checkpoints"  # QLoRA 체크포인트 저장 경로
    qlora_use_4bit: bool = True  # 4-bit 양자화 사용
    qlora_bnb_4bit_compute_dtype: str = "float16"  # BitsAndBytes 계산 dtype
    qlora_bnb_4bit_quant_type: str = "nf4"  # 양자화 타입
    qlora_bnb_4bit_use_double_quant: bool = True  # 이중 양자화 사용
    qlora_device_map: str = "auto"  # QLoRA device_map 설정

    # 인감도장/서명 검출 (YOLO + PyMuPDF)
    yolo_model_path: str = "models/stamp_detector/best.pt"  # YOLO_MODEL_PATH
    conf_thres: float = 0.05  # CONF_THRES: 검출 신뢰도 (현재 데이터 기준으로는 0.05에서 검출됨, 데이터 추가 후 상향 가능)
    render_dpi: int = 250  # RENDER_DPI: PDF→이미지 렌더링 DPI (200~300)
    max_pages: int = 50  # MAX_PAGES: 처리할 최대 페이지 수
    save_debug_images: bool = False  # SAVE_DEBUG_IMAGES: 디버그용 이미지 저장 여부

    def get_database_url(self) -> str:
        """Get PostgreSQL connection string.

        Returns:
            PostgreSQL connection URL string.
        """
        # DATABASE_URL 환경 변수가 있으면 우선 사용
        if self.database_url:
            return self.database_url

        # 그렇지 않으면 개별 파라미터로 구성
        ssl_param = f"?sslmode={self.postgres_sslmode}" if self.postgres_sslmode else ""
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}{ssl_param}"
        )

    class Config:
        """Pydantic configuration."""
        # 환경 변수가 우선하고, .env 파일은 fallback으로 사용
        # systemd의 EnvironmentFile로 환경 변수가 설정되면 그것을 사용
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"  # Ignore extra environment variables
        # 환경 변수 우선순위: 환경 변수 > .env 파일 > 기본값


# Global settings instance
settings = Settings()
