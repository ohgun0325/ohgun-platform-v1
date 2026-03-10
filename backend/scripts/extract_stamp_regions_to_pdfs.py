"""
전체 PDF에서 인감이 있는 페이지만 골라 한 PDF로 묶어 pdfs/에 저장합니다.

[1단계: YOLO 없이 확인]
  --pages 로 페이지 번호만 지정하면, YOLO 없이 해당 페이지만 추출해 pdfs/에 저장합니다.
  예: python scripts/extract_stamp_regions_to_pdfs.py --test-koica --pages 1
  → 전체 PDF의 1페이지만 추출해 data/koica_stamp_dataset/pdfs/에 저장.

[2단계: YOLO 사용 (나중에)]
  --pages 없이 --min-stamps 를 쓰면, YOLO로 인감 개수 보고 페이지를 골라 저장합니다.

사용법:
  python scripts/extract_stamp_regions_to_pdfs.py --test-koica --pages 1
  python scripts/extract_stamp_regions_to_pdfs.py --pdf path/to/full.pdf --output result.pdf --pages 1,3,5
  python scripts/extract_stamp_regions_to_pdfs.py --pdf path/to/full.pdf --pages 1-5
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Tuple

# 프로젝트 루트
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


def safe_stem(name: str) -> str:
    return "".join(c if c.isalnum() or c in "._-" else "_" for c in name)


def parse_pages(s: str, max_pages: int) -> List[int]:
    """'1,3,5' 또는 '1-5' 형식을 0-based 페이지 인덱스 리스트로 변환."""
    out: List[int] = []
    for part in s.strip().split(","):
        part = part.strip()
        if "-" in part:
            a, b = part.split("-", 1)
            lo, hi = int(a.strip()), int(b.strip())
            for i in range(max(1, lo), min(hi, max_pages) + 1):
                out.append(i - 1)  # 1-based → 0-based
        else:
            i = int(part)
            if 1 <= i <= max_pages:
                out.append(i - 1)
    return sorted(set(out))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="전체 PDF에서 인감이 N개 이상 있는 페이지만 골라 한 PDF로 저장합니다."
    )
    parser.add_argument(
        "--pdf",
        type=Path,
        default=None,
        help="전체 원본 PDF 경로 (--test-koica 사용 시 생략 가능)",
    )
    parser.add_argument(
        "--dataset-dir",
        type=Path,
        default=Path("data/koica_stamp_dataset"),
        help="데이터셋 루트 (출력: dataset_dir/pdfs/, 기본: data/koica_stamp_dataset)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help='출력 PDF 파일명 (기본: 원본이름_직인페이지만.pdf). 예: "키르기스스탄 PMC 부분_(직인 제출서류).pdf"',
    )
    parser.add_argument(
        "--min-stamps",
        type=int,
        default=5,
        help="이 개수 이상 인감이 검출된 페이지만 추출 (기본 5, 세로로 5개 인감 페이지)",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=250,
        help="PDF 렌더링 DPI (기본 250)",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=500,
        help="원본 PDF 최대 페이지 (기본 500)",
    )
    parser.add_argument(
        "--test-koica",
        action="store_true",
        help="테스트: 키르기스스탄 PMC 직인 제출서류 PDF로 실행 (한글 경로 회피용)",
    )
    parser.add_argument(
        "--pages",
        type=str,
        default=None,
        help="추출할 페이지 번호 (1부터 시작). 예: 1 또는 1,3,5 또는 1-5. 지정 시 YOLO 없이 해당 페이지만 추출.",
    )
    args = parser.parse_args()

    if args.test_koica:
        args.pdf = Path("data/koica_reports_origin/키르기스스탄 PMC_(직인 제출서류).pdf")
        args.output = "키르기스스탄 PMC 부분_(직인 제출서류).pdf"
        args.min_stamps = 5
    if args.pdf is None:
        print("오류: --pdf 경로를 지정하거나 --test-koica를 사용하세요.")
        sys.exit(1)

    pdf_path = args.pdf if args.pdf.is_absolute() else (_PROJECT_ROOT / args.pdf)
    if not pdf_path.is_file() and not pdf_path.name.startswith("."):
        # 파일명만 넘긴 경우: data/koica_reports_origin 에서 찾기
        alt = _PROJECT_ROOT / "data" / "koica_reports_origin" / pdf_path.name
        if alt.is_file():
            pdf_path = alt
    if not pdf_path.is_file():
        print(f"오류: 파일 없음: {pdf_path}")
        sys.exit(1)

    dataset_dir = args.dataset_dir if args.dataset_dir.is_absolute() else (_PROJECT_ROOT / args.dataset_dir)
    out_pdf_dir = dataset_dir / "pdfs"
    out_pdf_dir.mkdir(parents=True, exist_ok=True)

    import fitz

    src_doc = fitz.open(str(pdf_path))
    num_pages = len(src_doc)

    # ---- 1단계: YOLO 없이 페이지 번호로만 추출 ----
    if args.pages is not None:
        selected = parse_pages(args.pages, num_pages)
        if not selected:
            print(f"오류: 유효한 페이지가 없습니다. (원본 {num_pages}페이지, --pages {args.pages!r})")
            src_doc.close()
            sys.exit(1)
        print(f"YOLO 없이 지정 페이지만 추출: {[p + 1 for p in selected]} (총 {len(selected)}페이지)")
        out_doc = fitz.open()
        for i in selected:
            out_doc.insert_pdf(src_doc, from_page=i, to_page=i)
        src_doc.close()
        out_name = args.output or f"{pdf_path.stem}_직인페이지만.pdf"
        if not out_name.lower().endswith(".pdf"):
            out_name += ".pdf"
        out_path = out_pdf_dir / out_name
        out_doc.save(str(out_path))
        out_doc.close()
        print(f"완료: {out_path}")
        print("다음: python scripts/pdf_pages_to_train_images.py --dataset-dir", args.dataset_dir)
        return

    # ---- 2단계: YOLO로 인감 개수 보고 페이지 선택 ----
    src_doc.close()

    import os
    _yolo_path = os.environ.get("YOLO_MODEL_PATH", "models/stamp_detector/best.pt")
    _conf_thres = float(os.environ.get("CONF_THRES", "0.25"))
    from app.domain.detect.services.pdf_renderer import render_pdf_to_images
    from app.domain.detect.services.stamp_detector import StampDetector

    model_path = Path(_yolo_path)
    if not model_path.is_absolute():
        model_path = _PROJECT_ROOT / model_path
    if not model_path.exists():
        print(f"오류: YOLO 모델 없음: {model_path}")
        sys.exit(1)

    detector = StampDetector(model_path=str(model_path), conf_thres=_conf_thres)
    detector.load()

    try:
        images = render_pdf_to_images(
            pdf_path,
            dpi=args.dpi,
            max_pages=args.max_pages,
        )
    except Exception as e:
        print(f"오류: PDF 렌더링 실패: {e}")
        sys.exit(1)

    min_stamps = max(1, args.min_stamps)
    selected = []
    for page_idx, img in enumerate(images):
        detections: List[Tuple[str, float, Tuple[float, float, float, float]]] = detector.predict(img)
        if len(detections) >= min_stamps:
            selected.append(page_idx)
            print(f"  페이지 {page_idx + 1}: 인감 {len(detections)}개 → 추출 대상")

    if not selected:
        print(f"조건 충족 페이지 없음 (인감 {min_stamps}개 이상인 페이지 0건). 종료.")
        sys.exit(0)

    src_doc = fitz.open(str(pdf_path))
    out_doc = fitz.open()
    for i in selected:
        out_doc.insert_pdf(src_doc, from_page=i, to_page=i)
    src_doc.close()

    out_name = args.output or f"{pdf_path.stem}_직인페이지만.pdf"
    if not out_name.lower().endswith(".pdf"):
        out_name += ".pdf"
    out_path = out_pdf_dir / out_name
    out_doc.save(str(out_path))
    out_doc.close()

    print(f"\n완료: {len(selected)}페이지 → {out_path}")
    print("다음: python scripts/pdf_pages_to_train_images.py --dataset-dir", args.dataset_dir)


if __name__ == "__main__":
    main()
