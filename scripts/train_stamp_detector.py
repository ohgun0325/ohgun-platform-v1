"""
인감도장 YOLO 모델 학습.
data/koica_stamp_dataset (data.yaml + images/train,val + labels/train,val) 기준으로 학습 후
best.pt 를 models/stamp_detector/best.pt 로 복사합니다.

사용법 (프로젝트 루트에서):
  python scripts/train_stamp_detector.py
  python scripts/train_stamp_detector.py --epochs 50 --device cpu
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    parser = argparse.ArgumentParser(description="인감도장 YOLO 모델 학습")
    parser.add_argument("--epochs", type=int, default=100, help="학습 에폭 (기본 100)")
    parser.add_argument("--batch", type=int, default=16, help="배치 크기 (기본 16)")
    parser.add_argument("--imgsz", type=int, default=640, help="이미지 크기 (기본 640)")
    parser.add_argument("--device", type=str, default="0", help="GPU 번호 또는 cpu")
    parser.add_argument("--no-copy", action="store_true", help="학습만 하고 models/stamp_detector 로 복사 안 함")
    args = parser.parse_args()

    data_yaml = _PROJECT_ROOT / "data" / "koica_stamp_dataset" / "data.yaml"
    if not data_yaml.is_file():
        print(f"오류: 데이터 설정 없음: {data_yaml}")
        sys.exit(1)

    try:
        from ultralytics import YOLO
    except ImportError:
        print("오류: ultralytics 가 필요합니다. pip install ultralytics")
        sys.exit(1)

    model = YOLO("yolov8n.pt")
    results = model.train(
        data=str(data_yaml),
        epochs=args.epochs,
        batch=args.batch,
        imgsz=args.imgsz,
        device=args.device,
        project=str(_PROJECT_ROOT / "runs" / "detect"),
        name="stamp_detector",
        exist_ok=True,
    )

    best_pt = Path(results.save_dir) / "weights" / "best.pt"
    if not best_pt.is_file():
        # ultralytics 버전에 따라 save_dir 경로가 다를 수 있음
        alt = _PROJECT_ROOT / "runs" / "detect" / "stamp_detector" / "weights" / "best.pt"
        if alt.is_file():
            best_pt = alt
        else:
            print("경고: best.pt 를 찾지 못했습니다. runs/detect/stamp_detector/ 아래를 확인하세요.")
            return

    if not args.no_copy:
        dest_dir = _PROJECT_ROOT / "models" / "stamp_detector"
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / "best.pt"
        shutil.copy2(best_pt, dest)
        print(f"\n복사 완료: {best_pt} → {dest}")
        print("API 사용을 위해 서버를 재시작하세요 (python run.py).")


if __name__ == "__main__":
    main()
