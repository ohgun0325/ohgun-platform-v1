"""KOICA 테스트셋(koica_data_test.jsonl) 기반 Q&A 조회 서비스.

목표:
- 사용자가 KOICA 데이터와 관련된 질문을 할 때,
  `data/koica_data/koica_data_test.jsonl`에서 가장 유사한 항목을 찾아
  해당 항목의 `output`을 그대로 반환한다.

데이터 스키마(예상):
{"instruction": "...", "input": "...", "output": "..."}
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import List, Optional, Tuple


def _project_root() -> Path:
    # app/domain/koica/services/... → 프로젝트 루트
    return Path(__file__).resolve().parents[4]


def _default_test_path() -> Path:
    return _project_root() / "data" / "koica_data" / "koica_data_test.jsonl"


def _read_text_lines(path: Path) -> List[str]:
    encodings = ["utf-8", "utf-8-sig", "cp949", "euc-kr"]
    last_err: Optional[Exception] = None
    for enc in encodings:
        try:
            return path.read_text(encoding=enc).splitlines()
        except Exception as e:  # noqa: BLE001 - 여러 인코딩 시도
            last_err = e
            continue
    raise RuntimeError(f"koica_data_test.jsonl 읽기 실패: {path}") from last_err


def _normalize(text: str) -> str:
    t = text.strip().lower()
    t = re.sub(r"\s+", " ", t)
    return t


@dataclass(frozen=True)
class KoicaQAItem:
    instruction: str
    input: str
    output: str


class KoicaTestQAService:
    """koica_data_test.jsonl을 로드하고 질의 유사도로 답변을 반환."""

    def __init__(self, dataset_path: Optional[Path] = None):
        self.dataset_path = dataset_path or _default_test_path()
        self._items: Optional[List[KoicaQAItem]] = None

    def is_available(self) -> bool:
        return self.dataset_path.exists()

    def _load(self) -> List[KoicaQAItem]:
        if self._items is not None:
            return self._items

        if not self.dataset_path.exists():
            self._items = []
            return self._items

        items: List[KoicaQAItem] = []
        for line in _read_text_lines(self.dataset_path):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue

            instruction = str(obj.get("instruction", "")).strip()
            input_text = str(obj.get("input", "")).strip()
            output_text = str(obj.get("output", "")).strip()
            if not input_text or not output_text:
                continue
            items.append(KoicaQAItem(instruction=instruction, input=input_text, output=output_text))

        self._items = items
        return items

    @staticmethod
    def _score(query: str, candidate: str) -> float:
        """간단 유사도 점수 (0~1)."""
        q = _normalize(query)
        c = _normalize(candidate)
        if not q or not c:
            return 0.0
        if q in c or c in q:
            return 1.0
        return SequenceMatcher(a=q, b=c).ratio()

    def find_best_answer(
        self,
        query: str,
        *,
        threshold: float = 0.62,
    ) -> Optional[Tuple[str, float, str]]:
        """query에 가장 유사한 test셋 output을 반환.

        Returns:
            (answer, score, matched_input) 또는 None
        """
        items = self._load()
        if not items:
            return None

        best_score = 0.0
        best: Optional[KoicaQAItem] = None
        for item in items:
            s = self._score(query, item.input)
            if s > best_score:
                best_score = s
                best = item

        if best is None or best_score < threshold:
            return None

        return best.output, best_score, best.input

