"""임베딩 기반 의미 매칭 유틸리티.

주요 목적:
- 필드 라벨(예: "담당자이름")과 실제 문서 라벨(예: "성명", "담당자명", "신청인")의
  의미적 유사도를 기반으로 최적 매칭을 찾기 위해 사용.
- KOICA 전반(제안서, 입찰서류, 계약서 등)에서 공통으로 재사용 가능하도록
  OCR/도메인 로직과 분리된 순수 유틸로 설계.

기본 임베딩 모델:
- dragonkue/multilingual-e5-small-ko-v2
  - 384차원, 한국어/멀티링구얼, E5 계열 (retrieval/RAG 최적화)
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import List, Sequence, Tuple

import logging
import numpy as np
from sentence_transformers import SentenceTransformer


logger = logging.getLogger(__name__)

def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """단일 벡터 간 코사인 유사도."""
    denom = (np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0.0:
        return 0.0
    return float(np.dot(a, b) / denom)


class SemanticFieldMatcher:
    """임베딩 기반 필드/라벨 의미 매칭기.

    - target_field: 내부 논리 필드명 (예: "담당자이름")
    - candidate_labels: 문서/화면에 실제로 등장하는 라벨 텍스트 (예: ["성명", "담당자명", "신청인"])
    """

    def __init__(
        self,
        model_name: str | None = None,
        device: str | None = None,
    ) -> None:
        # 환경 변수 우선, 없으면 기본값 사용
        if model_name is None:
            model_name = os.getenv(
                "SEMANTIC_EMBEDDING_MODEL_NAME",
                "dragonkue/multilingual-e5-small-ko-v2",
            )
        if device is None:
            device = os.getenv("EMBEDDING_DEVICE", "cpu")

        self.model_name = model_name
        self.device = device
        logger.info(
            "[SemanticFieldMatcher] 모델 초기화: %s (device=%s)",
            self.model_name,
            self.device,
        )
        self._model = SentenceTransformer(model_name, device=device)

    def encode(self, texts: Sequence[str]) -> np.ndarray:
        """문자열 시퀀스를 임베딩 행렬로 인코딩."""
        if not texts:
            return np.zeros((0, 0), dtype=np.float32)
        emb = self._model.encode(
            list(texts),
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
        # sentence-transformers는 (N, D) 형태 반환
        return emb.astype(np.float32)

    def find_best_match(
        self,
        target_field: str,
        candidate_labels: Sequence[str],
        threshold: float = 0.7,
    ) -> Tuple[str, float]:
        """단일 타겟 필드에 대한 최적 라벨과 유사도 점수 반환.

        Args:
            target_field: 논리 필드명 (예: "담당자이름")
            candidate_labels: 문서 내 실제 라벨 텍스트들
            threshold: 최소 코사인 유사도 임계값 (0.0~1.0)

        Returns:
            (매칭된 라벨, 유사도 점수). 임계값 미만일 경우 ("", 0.0) 반환.
        """
        if not candidate_labels:
            return "", 0.0

        target_emb = self.encode([target_field])[0]  # (D,)
        cand_embs = self.encode(candidate_labels)    # (N, D)
        if cand_embs.size == 0:
            return "", 0.0

        # normalize_embeddings=True 이므로 dot product가 곧 코사인 유사도
        sims = cand_embs @ target_emb
        best_idx = int(np.argmax(sims))
        best_score = float(sims[best_idx])

        if best_score < threshold:
            logger.info(
                "[SemanticFieldMatcher] 매칭 실패: target=%r, candidates=%d, best_score=%.3f < threshold=%.3f",
                target_field,
                len(candidate_labels),
                best_score,
                threshold,
            )
            return "", 0.0
        logger.info(
            "[SemanticFieldMatcher] 매칭 성공: target=%r, best_label=%r, score=%.3f, threshold=%.3f",
            target_field,
            candidate_labels[best_idx],
            best_score,
            threshold,
        )
        return candidate_labels[best_idx], best_score

    def rank_candidates(
        self,
        query: str,
        candidates: Sequence[str],
        top_k: int = 5,
    ) -> List[Tuple[str, float]]:
        """쿼리와 가장 유사한 후보들을 점수 순으로 반환.

        OCR 후 라벨/섹션 후보를 점수와 함께 보고 싶을 때 사용.
        """
        if not candidates:
            return []

        query_emb = self.encode([query])[0]
        cand_embs = self.encode(candidates)
        if cand_embs.size == 0:
            return []

        sims = cand_embs @ query_emb
        indices = np.argsort(sims)[::-1][:top_k]
        ranked = [(candidates[int(i)], float(sims[int(i)])) for i in indices]
        preview = ", ".join(
            f"{label[:12]!r}:{score:.3f}" for label, score in ranked[:3]
        )
        logger.info(
            "[SemanticFieldMatcher] rank_candidates: query=%r, candidates=%d, top_k=%d, top3=[%s]",
            query,
            len(candidates),
            top_k,
            preview,
        )
        return ranked


@lru_cache(maxsize=2)
def get_default_semantic_matcher() -> SemanticFieldMatcher:
    """프로세스 전역에서 재사용할 디폴트 매처 인스턴스."""
    return SemanticFieldMatcher()

