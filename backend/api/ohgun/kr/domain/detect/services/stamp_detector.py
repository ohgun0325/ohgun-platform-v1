"""YOLO(ultralytics) 기반 인감도장/서명 객체 검출.

- 앱 시작 시 1회 로드, 매 요청마다 재로드 금지.
- 클래스: stamp, signature (모델에 signature가 없으면 signature는 항상 False).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, List, Optional, Tuple

# 클래스명 매핑 (YOLO class index → 이름). 모델 학습 시 정의에 맞게 수정.
CLASS_NAMES = ("stamp", "signature")


class StampDetector:
    """YOLO 모델을 사용한 인감도장/서명 검출기."""

    def __init__(
        self,
        model_path: str,
        conf_thres: float = 0.35,
    ):
        """검출기 초기화. load() 호출 전까지 모델은 로드되지 않습니다.

        Args:
            model_path: YOLO 모델 파일 경로 (e.g. best.pt).
            conf_thres: 검출 신뢰도 임계값 (0~1).
        """
        self.model_path = Path(model_path)
        self.conf_thres = max(0.0, min(1.0, conf_thres))
        self._model: Any = None
        self._class_names: Tuple[str, ...] = CLASS_NAMES

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    def load(self) -> None:
        """모델을 로드합니다. 이미 로드된 경우 무시합니다."""
        if self._model is not None:
            return
        if not self.model_path.exists():
            raise FileNotFoundError(
                f"YOLO 모델을 찾을 수 없습니다: {self.model_path}. "
                "YOLO_MODEL_PATH 환경변수를 확인하세요."
            )
        from ultralytics import YOLO  # type: ignore[import-untyped]
        self._model = YOLO(str(self.model_path))
        # 모델에 정의된 클래스명이 있으면 사용 (학습 시 names)
        # - dict: {class_id: name}
        # - list/tuple: [name0, name1, ...]
        # CLASS_NAMES 길이보다 많은 클래스가 있을 수 있으므로,
        # 인덱스로 CLASS_NAMES를 참조하지 않고 모델이 가진 names만 사용한다.
        if hasattr(self._model, "model") and hasattr(self._model.model, "names"):
            names = self._model.model.names
            if isinstance(names, dict) and names:
                keys = sorted(names.keys())
                self._class_names = tuple(str(names[k]) for k in keys)
            elif isinstance(names, (list, tuple)) and len(names) > 0:
                self._class_names = tuple(str(n) for n in names)

    def predict(
        self,
        image: Any,
    ) -> List[Tuple[str, float, Tuple[float, float, float, float]]]:
        """단일 이미지에서 stamp/signature 검출.

        Args:
            image: PIL Image 또는 numpy array (RGB).

        Returns:
            [(cls, conf, (x1,y1,x2,y2)), ...] 리스트.
        """
        if self._model is None:
            raise RuntimeError("모델이 로드되지 않았습니다. load()를 먼저 호출하세요.")

        import numpy as np
        from PIL import Image

        if isinstance(image, Image.Image):
            img_np = np.array(image)
        else:
            img_np = image

        results = self._model.predict(
            img_np,
            conf=self.conf_thres,
            verbose=False,
        )

        out: List[Tuple[str, float, Tuple[float, float, float, float]]] = []
        if not results:
            return out

        r = results[0]
        if r.boxes is None:
            return out

        boxes = r.boxes
        for i in range(len(boxes)):
            xyxy = boxes.xyxy[i].cpu().numpy()
            conf = float(boxes.conf[i].cpu().numpy())
            cls_id = int(boxes.cls[i].cpu().numpy())
            cls_name = self._class_names[cls_id] if cls_id < len(self._class_names) else "stamp"
            out.append((cls_name, conf, (float(xyxy[0]), float(xyxy[1]), float(xyxy[2]), float(xyxy[3]))))

        return out

    def has_stamp(self, detections: List[Tuple[str, float, Tuple[float, float, float, float]]]) -> bool:
        """검출 목록에 인감도장(stamp)이 하나라도 있는지.

        현재 KOICA용 모델은 'postec', 'idino' 등 여러 직인 클래스를 사용하므로,
        클래스 이름이 무엇이든 '무언가가 검출되기만 하면' 인감도장이 있다고 판단한다.
        (서명은 별도 signature 클래스를 학습했을 때만 감지)
        """
        return len(detections) > 0

    def has_signature(self, detections: List[Tuple[str, float, Tuple[float, float, float, float]]]) -> bool:
        """검출 목록에 signature가 하나라도 있는지. 모델에 signature 클래스가 없으면 False."""
        return any(cls == "signature" for cls, _, _ in detections)
