"""로컬 Hugging Face 임베딩 모델 클라이언트.

artifacts 폴더에 저장된 임베딩 모델을 사용하여 벡터를 생성합니다.

기본 임베딩 모델은 한국어/멀티링구얼에 최적화된
`dragonkue/multilingual-e5-small-ko-v2`(384차원) 를 권장합니다.
"""
import os
import logging
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)

try:
    from langchain_community.embeddings import HuggingFaceEmbeddings
    from langchain_core.embeddings import Embeddings
    HF_EMBEDDINGS_AVAILABLE = True
except ImportError:
    HF_EMBEDDINGS_AVAILABLE = False
    logger.warning("langchain-community가 설치되지 않았습니다. pip install langchain-community 를 실행하세요.")


class EmbeddingClient:
    """로컬 Hugging Face 임베딩 모델을 사용하는 클라이언트.
    
    기본 추천 모델:
    - dragonkue/multilingual-e5-small-ko-v2 (384차원, 한국어/멀티링구얼, E5 계열)
    
    필요에 따라 EMBEDDING_MODEL_NAME 환경 변수로 교체할 수 있습니다.
    """

    def __init__(self, model_path: Optional[str] = None):
        """EmbeddingClient 초기화.

        Args:
            model_path: 로컬 모델 경로. None이면 환경 변수 또는 기본 경로 사용.
        """
        if not HF_EMBEDDINGS_AVAILABLE:
            raise ImportError(
                "Hugging Face embeddings를 사용할 수 없습니다. "
                "pip install langchain-community sentence-transformers 를 실행하세요."
            )

        # 모델 경로 결정
        if model_path is None:
            # 환경 변수에서 경로 가져오기
            model_path = os.getenv(
                "EMBEDDING_MODEL_PATH",
                None
            )

            # 환경 변수가 없으면 기본 경로 사용
            if model_path is None:
                # artifacts/embedding-models/dragonkue--multilingual-e5-small-ko-v2 (app/spokes/infrastructure → 루트 = 4단계)
                project_root = Path(__file__).resolve().parent.parent.parent.parent
                default_model_name = os.getenv(
                    "EMBEDDING_MODEL_NAME",
                    "dragonkue/multilingual-e5-small-ko-v2",  # 384차원 한국어 특화/멀티링구얼 E5 모델
                )
                # Hugging Face 모델 이름을 경로로 변환 (슬래시를 --로)
                model_dir_name = default_model_name.replace("/", "--")
                model_path = project_root / "artifacts" / "embedding-models" / model_dir_name

        self.model_path = Path(model_path) if model_path else None
        self.embeddings: Optional[Embeddings] = None
        self._initialize_embeddings()

    def _initialize_embeddings(self):
        """임베딩 모델을 초기화합니다."""
        try:
            # 로컬 경로가 존재하는지 확인
            if self.model_path and self.model_path.exists():
                logger.info(f"[임베딩 클라이언트] 로컬 모델 로딩: {self.model_path}")
                model_name = str(self.model_path)
            else:
                # 로컬 경로가 없으면 Hugging Face Hub에서 다운로드
                model_name = os.getenv(
                    "EMBEDDING_MODEL_NAME",
                    "jhgan/ko-sroberta-multitask"  # 768차원 한국어 특화 모델
                )
                logger.info(f"[임베딩 클라이언트] Hugging Face Hub에서 모델 로딩: {model_name}")
                logger.info("[임베딩 클라이언트] 모델이 artifacts 폴더에 자동으로 다운로드됩니다.")

            # HuggingFaceEmbeddings 초기화
            # cache_folder를 artifacts/embedding-models로 설정하여 로컬에 저장
            project_root = Path(__file__).resolve().parent.parent.parent.parent
            cache_folder = project_root / "artifacts" / "embedding-models"
            cache_folder.mkdir(parents=True, exist_ok=True)

            self.embeddings = HuggingFaceEmbeddings(
                model_name=model_name,
                cache_folder=str(cache_folder),
                model_kwargs={
                    "device": os.getenv("EMBEDDING_DEVICE", "cpu"),  # GPU 사용 시 "cuda"
                },
                encode_kwargs={
                    "normalize_embeddings": True,  # 벡터 정규화
                    "batch_size": 32,  # 배치 처리로 성능 향상
                }
            )

            logger.info("[임베딩 클라이언트] 임베딩 모델 초기화 완료")

        except Exception as e:
            logger.error(f"[임베딩 클라이언트] 모델 초기화 실패: {str(e)}", exc_info=True)
            raise

    async def get_embedding(self, text: str) -> List[float]:
        """텍스트에 대한 임베딩 벡터를 생성합니다.

        Args:
            text: 임베딩할 텍스트

        Returns:
            임베딩 벡터 (기본 384차원, 모델에 따라 상이)
        """
        if self.embeddings is None:
            raise RuntimeError("임베딩 모델이 초기화되지 않았습니다.")

        try:
            # LangChain의 embed_query 메서드 사용
            # 이 메서드는 동기 함수이므로 asyncio.to_thread로 비동기 실행
            import asyncio
            logger.info(
                "[임베딩 클라이언트] async 임베딩 요청: text_len=%d",
                len(text or ""),
            )
            vector = await asyncio.to_thread(self.embeddings.embed_query, text)
            logger.info(
                "[임베딩 클라이언트] async 임베딩 완료: dim=%d",
                len(vector) if isinstance(vector, list) else 0,
            )
            return vector
        except Exception as e:
            logger.error(f"[임베딩 클라이언트] 임베딩 생성 실패: {str(e)}", exc_info=True)
            raise

    def get_embedding_sync(self, text: str) -> List[float]:
        """텍스트에 대한 임베딩 벡터를 동기적으로 생성합니다.

        Args:
            text: 임베딩할 텍스트

        Returns:
            임베딩 벡터 (기본 384차원, 모델에 따라 상이)
        """
        if self.embeddings is None:
            raise RuntimeError("임베딩 모델이 초기화되지 않았습니다.")

        try:
            logger.info(
                "[임베딩 클라이언트] sync 임베딩 요청: text_len=%d",
                len(text or ""),
            )
            vector = self.embeddings.embed_query(text)
            logger.info(
                "[임베딩 클라이언트] sync 임베딩 완료: dim=%d",
                len(vector) if isinstance(vector, list) else 0,
            )
            return vector
        except Exception as e:
            logger.error(f"[임베딩 클라이언트] 임베딩 생성 실패: {str(e)}", exc_info=True)
            raise

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """여러 텍스트에 대한 임베딩 벡터를 배치로 생성합니다.
        DB 데이터 벡터화(players_embeddings 등) 전용으로 사용합니다.

        Args:
            texts: 임베딩할 텍스트 리스트

        Returns:
            임베딩 벡터 리스트 (기본 384차원, 모델에 따라 상이)
        """
        if self.embeddings is None:
            raise RuntimeError("임베딩 모델이 초기화되지 않았습니다.")
        if not texts:
            return []
        try:
            logger.info(
                "[임베딩 클라이언트] 배치 임베딩 요청: count=%d, 예시_길이=%d",
                len(texts),
                len(texts[0]) if texts else 0,
            )
            vectors = self.embeddings.embed_documents(texts)
            dim = len(vectors[0]) if vectors else 0
            logger.info(
                "[임베딩 클라이언트] 배치 임베딩 완료: count=%d, dim=%d",
                len(vectors),
                dim,
            )
            return vectors
        except Exception as e:
            logger.error(f"[임베딩 클라이언트] 배치 임베딩 생성 실패: {str(e)}", exc_info=True)
            raise
