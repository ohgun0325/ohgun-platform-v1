"""KOICA 보고서 SFT JSONL을 train/val/test로 분할합니다.

입력: data/koica_reports/koica_reports.sft.jsonl
출력:
  - data/koica_reports/koica_reports_train.jsonl (80%)
  - data/koica_reports/koica_reports_val.jsonl (10%)
  - data/koica_reports/koica_reports_test.jsonl (10%)

고정 시드(42)로 재현 가능하게 분할합니다.

실행 (프로젝트 루트에서):
  python scripts/split_koica_reports_sft.py
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = ROOT / "data" / "koica_reports"
SFT_FILE = REPORTS_DIR / "koica_reports.sft.jsonl"

TRAIN_RATIO = 0.8
VAL_RATIO = 0.1
TEST_RATIO = 0.1
SEED = 42


def main() -> int:
    if not SFT_FILE.exists():
        print(f"[오류] 파일 없음: {SFT_FILE}")
        return 1

    records = []
    with open(SFT_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    if not records:
        print("[오류] 유효한 레코드가 없습니다.")
        return 1

    n = len(records)
    random.seed(SEED)
    indices = list(range(n))
    random.shuffle(indices)

    n_train = int(n * TRAIN_RATIO)
    n_val = int(n * VAL_RATIO)
    n_test = n - n_train - n_val  # 나머지는 test

    train_idx = set(indices[:n_train])
    val_idx = set(indices[n_train : n_train + n_val])
    test_idx = set(indices[n_train + n_val :])

    train_records = [r for i, r in enumerate(records) if i in train_idx]
    val_records = [r for i, r in enumerate(records) if i in val_idx]
    test_records = [r for i, r in enumerate(records) if i in test_idx]

    def write_jsonl(path: Path, data: list) -> None:
        with open(path, "w", encoding="utf-8") as f:
            for rec in data:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    write_jsonl(REPORTS_DIR / "koica_reports_train.jsonl", train_records)
    write_jsonl(REPORTS_DIR / "koica_reports_val.jsonl", val_records)
    write_jsonl(REPORTS_DIR / "koica_reports_test.jsonl", test_records)

    print(f"[분할 완료] 시드={SEED}, 비율 train/val/test = {TRAIN_RATIO}/{VAL_RATIO}/{TEST_RATIO}")
    print(f"  - train: {len(train_records)}건 → {REPORTS_DIR / 'koica_reports_train.jsonl'}")
    print(f"  - val:   {len(val_records)}건 → {REPORTS_DIR / 'koica_reports_val.jsonl'}")
    print(f"  - test:  {len(test_records)}건 → {REPORTS_DIR / 'koica_reports_test.jsonl'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
