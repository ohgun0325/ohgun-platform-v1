"""경기장 데이터에 대한 정책 기반(LLM 에이전트) 처리 로직.

현재는 예시/스켈레톤 구현으로, 실제 비즈니스 로직은 추후 확장합니다.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from artifacts.models.core.manager import ModelManager


class StadiumAgent:
    """정책 기반(LLM) 전략 — 경기장.

    LLM을 활용하여 업로드된 경기장 데이터를 해석/요약하거나,
    도메인 규칙을 학습된 정책으로 대체하는 역할을 합니다.
    """

    def __init__(self, model_name: Optional[str] = None) -> None:
        self.model_name = model_name or "monolog/koelectra-small-v3-discriminator"
        self._model = None

    def _ensure_model(self) -> None:
        if self._model is None:
            manager = ModelManager()
            self._model = manager.get_chat_model(self.model_name)
            if self._model is None:
                raise RuntimeError(
                    f"정책 기반 모델을 로드할 수 없습니다. model_name={self.model_name!r}"
                )

    def process(
        self,
        records: List[Dict[str, Any]],
        data_type: str,
        file_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """정책 기반(LLM)으로 경기장 데이터를 처리합니다.

        현재는 간단한 요약 텍스트를 생성하는 예시 구현입니다.
        """
        self._ensure_model()

        preview_text_lines = []
        for idx, row in enumerate(records[:5], start=1):
            preview_text_lines.append(f"[{idx}] {row}")
        preview_text = "\n".join(preview_text_lines)

        system_prompt = (
            "당신은 축구 경기장 데이터 품질을 점검하고, 정책 기반(룰 기반이 아닌) 모델링이 "
            "적합한지 판단하고 요약을 작성하는 데이터 분석가입니다."
        )
        user_prompt = (
            f"다음은 '{data_type}' 타입의 경기장 데이터 예시입니다 (파일: {file_name}).\n\n"
            f"{preview_text}\n\n"
            "이 데이터를 바탕으로 어떤 정책/규칙을 학습할 수 있을지 한국어로 간단히 요약해 주세요."
        )

        response = self._model.invoke(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]
        )

        return {
            "mode": "policy",
            "model_name": self.model_name,
            "summary": response,
            "record_count": len(records),
        }
