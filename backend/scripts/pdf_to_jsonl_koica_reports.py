"""KOICA 보고서 PDF를 JSONL로 전처리합니다.

data/koica_reports/*.pdf 를 읽어 페이지별 텍스트·표를 추출하고
data/koica_reports/koica_reports.jsonl 로 저장합니다.
AI 모델 훈련·임베딩용으로 사용할 수 있습니다.

실행 (프로젝트 루트에서):
  python scripts/pdf_to_jsonl_koica_reports.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PDF_DIR = ROOT / "data" / "koica_reports"
OUT_JSONL = ROOT / "data" / "koica_reports" / "koica_reports.jsonl"


def table_to_text(table: list[list[str | None]]) -> str:
    """2차원 표를 읽기 쉬운 텍스트로 변환."""
    if not table:
        return ""
    lines = []
    for row in table:
        cells = [str(c).strip() if c else "" for c in row]
        lines.append(" | ".join(cells))
    return "\n".join(lines)


def process_pdf(pdf_path: Path) -> list[dict]:
    """단일 PDF에서 페이지별 텍스트·표를 추출해 레코드 리스트 반환."""
    import pdfplumber

    records = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            text = page.extract_text()
            tables = page.extract_tables() or []
            table_texts = [table_to_text(t) for t in tables if t]
            combined_text = (text or "").strip()
            if table_texts:
                combined_text += "\n\n[표]\n" + "\n\n".join(table_texts)

            if not combined_text.strip():
                continue

            records.append({
                "source": pdf_path.name,
                "page": i,
                "text": combined_text.strip(),
            })
    return records


def main() -> int:
    if not PDF_DIR.exists():
        print(f"[오류] 폴더 없음: {PDF_DIR}")
        return 1

    pdf_files = sorted(PDF_DIR.glob("*.pdf"))
    if not pdf_files:
        print(f"[오류] PDF 파일 없음: {PDF_DIR}")
        return 1

    print(f"[1/2] PDF {len(pdf_files)}개 발견: {[p.name for p in pdf_files]}")

    all_records = []
    for pdf_path in pdf_files:
        try:
            recs = process_pdf(pdf_path)
            all_records.extend(recs)
            print(f"  - {pdf_path.name}: {len(recs)}페이지 추출")
        except Exception as e:
            print(f"[경고] {pdf_path.name} 처리 실패: {e}")
            continue

    if not all_records:
        print("[오류] 추출된 텍스트가 없습니다.")
        return 1

    OUT_JSONL.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_JSONL, "w", encoding="utf-8") as f:
        for rec in all_records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print(f"[2/2] 저장 완료: {OUT_JSONL} ({len(all_records)}건)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
