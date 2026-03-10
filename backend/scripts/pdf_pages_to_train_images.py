"""
PDF 폴더를 지정하면 페이지별로 이미지를 뽑아 images/train, images/val 구조로 저장합니다.
YOLO 인감도장 학습용 데이터셋 이미지를 PDF에서 자동 생성할 때 사용하세요.

사용법 (프로젝트 루트에서):

  # 데이터셋 루트만 지정: pdfs/ → images/train, images/val 자동 분할
  python scripts/pdf_pages_to_train_images.py --dataset-dir data/koica_stamp_dataset

  # 기존 방식: PDF 폴더와 출력 폴더 각각 지정
  python scripts/pdf_pages_to_train_images.py --pdf-dir data/koica_detect_row_pdfs --output-dir data/koica_stamp_dataset/images/train

저장 후에는 각 이미지에 대해 YOLO 형식 라벨 파일(labels/train/*.txt 등)을 작성해 주어야 합니다.
"""

from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path
from typing import Any, List, Tuple

# 프로젝트 루트를 path에 추가 (스크립트 위치에 관계없이 app import 가능하도록)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from app.domain.detect.services.pdf_renderer import render_pdf_to_images


def safe_stem(pdf_path: Path) -> str:
    """파일명에 사용하기에 부적절한 문자 치환."""
    stem = pdf_path.stem
    return "".join(c if c.isalnum() or c in "._-" else "_" for c in stem)


def run_single_dir(
    pdf_dir: Path,
    output_dir: Path,
    dpi: int,
    max_pages: int,
) -> int:
    """PDF 폴더 하나를 렌더링해 output_dir에 저장. 저장한 이미지 수 반환."""
    pdf_files = sorted(pdf_dir.glob("*.pdf"))
    if not pdf_files:
        return 0
    output_dir.mkdir(parents=True, exist_ok=True)
    total = 0
    for pdf_path in pdf_files:
        try:
            images = render_pdf_to_images(
                pdf_path,
                dpi=dpi,
                max_pages=max_pages,
            )
        except Exception as e:
            print(f"  건너뜀 ({pdf_path.name}): {e}")
            continue
        stem = safe_stem(pdf_path)
        for i, img in enumerate(images):
            out_path = output_dir / f"{stem}_p{i:04d}.png"
            img.save(out_path)
            total += 1
        print(f"  {pdf_path.name} → {len(images)}장")
    return total


def run_dataset_dir(
    dataset_dir: Path,
    dpi: int,
    max_pages: int,
    train_ratio: float,
    seed: int,
) -> None:
    """dataset_dir/pdfs/ 의 PDF를 렌더링해 train_ratio 비율로 images/train, images/val에 저장."""
    pdf_dir = dataset_dir / "pdfs"
    out_train = dataset_dir / "images" / "train"
    out_val = dataset_dir / "images" / "val"

    if not pdf_dir.is_dir():
        print(f"오류: PDF 폴더가 없습니다: {pdf_dir}")
        sys.exit(1)

    pdf_files = sorted(pdf_dir.glob("*.pdf"))
    if not pdf_files:
        print(f"경고: '{pdf_dir}'에 PDF가 없습니다.")
        sys.exit(0)

    # (safe_stem, page_idx, img) 수집
    items: List[Tuple[str, int, Any]] = []
    for pdf_path in pdf_files:
        try:
            images = render_pdf_to_images(
                pdf_path,
                dpi=dpi,
                max_pages=max_pages,
            )
        except Exception as e:
            print(f"  건너뜀 ({pdf_path.name}): {e}")
            continue
        stem = safe_stem(pdf_path)
        for i, img in enumerate(images):
            items.append((stem, i, img))
        print(f"  {pdf_path.name} → {len(images)}장 렌더링")

    if not items:
        print("저장할 이미지가 없습니다.")
        sys.exit(0)

    random.seed(seed)
    random.shuffle(items)
    n_train = max(1, int(len(items) * train_ratio))
    train_items = items[:n_train]
    val_items = items[n_train:]

    out_train.mkdir(parents=True, exist_ok=True)
    out_val.mkdir(parents=True, exist_ok=True)

    for stem, i, img in train_items:
        img.save(out_train / f"{stem}_p{i:04d}.png")
    for stem, i, img in val_items:
        img.save(out_val / f"{stem}_p{i:04d}.png")

    print(f"\n완료: PDF {len(pdf_files)}개 → 총 {len(items)}장 이미지")
    print(f"  train: {len(train_items)}장 → {out_train}")
    print(f"  val:   {len(val_items)}장 → {out_val}")
    print("다음 단계: 각 이미지에 대해 labels/train/*.txt, labels/val/*.txt (YOLO 형식) 라벨을 작성하세요.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="PDF를 페이지별 이미지로 렌더링해 images/train, images/val에 저장합니다."
    )
    parser.add_argument(
        "--dataset-dir",
        type=Path,
        default=None,
        help="데이터셋 루트 (지정 시 pdfs/ → images/train, images/val 자동 분할)",
    )
    parser.add_argument(
        "--pdf-dir",
        type=Path,
        default=None,
        help="PDF 폴더 (--dataset-dir 미사용 시 필수)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="출력 이미지 폴더 (--dataset-dir 미사용 시 사용, 기본: data/koica_stamp_dataset/images/train)",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=250,
        help="렌더링 DPI (200~300, 기본 250)",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=50,
        help="PDF당 최대 페이지 수 (기본 50)",
    )
    parser.add_argument(
        "--train-ratio",
        type=float,
        default=0.8,
        help="train 비율 (0~1, --dataset-dir 사용 시만, 기본 0.8)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="train/val 분할 시드 (--dataset-dir 사용 시만, 기본 42)",
    )
    args = parser.parse_args()

    if args.dataset_dir is not None:
        dataset_dir = args.dataset_dir if args.dataset_dir.is_absolute() else (_PROJECT_ROOT / args.dataset_dir)
        run_dataset_dir(
            dataset_dir=dataset_dir,
            dpi=args.dpi,
            max_pages=args.max_pages,
            train_ratio=args.train_ratio,
            seed=args.seed,
        )
        return

    # 기존 단일 출력 폴더 모드
    if args.pdf_dir is None:
        print("오류: --dataset-dir 또는 --pdf-dir 중 하나를 지정하세요.")
        sys.exit(1)
    pdf_dir = args.pdf_dir if args.pdf_dir.is_absolute() else (_PROJECT_ROOT / args.pdf_dir)
    output_dir = args.output_dir
    if output_dir is None:
        output_dir = _PROJECT_ROOT / "data" / "koica_stamp_dataset" / "images" / "train"
    elif not output_dir.is_absolute():
        output_dir = _PROJECT_ROOT / output_dir

    if not pdf_dir.is_dir():
        print(f"오류: PDF 폴더를 찾을 수 없습니다: {pdf_dir}")
        sys.exit(1)

    total = run_single_dir(
        pdf_dir=pdf_dir,
        output_dir=output_dir,
        dpi=args.dpi,
        max_pages=args.max_pages,
    )
    print(f"\n완료: 총 {total}장 이미지 → {output_dir}")
    print("다음 단계: 각 이미지에 대해 YOLO 형식 라벨 파일(labels/train/*.txt)을 작성하세요.")


if __name__ == "__main__":
    main()
