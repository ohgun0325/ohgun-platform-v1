# -*- coding: utf-8 -*-
"""사업유형별 ODA 실적통계 CSV → JSONL → SFT 변환 (한글 경로)."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
kr_root = ROOT / "api" / "ohgun" / "kr"
sys.path.insert(0, str(kr_root))

from domain.shared.services.convert_koica_to_jsonl import convert_csv_to_jsonl
from domain.shared.services.convert_koica_to_sft import convert_jsonl_to_sft

base = ROOT / "data" / "koica_data"
name = "한국국제협력단_사업유형별 ODA 실적통계_20241002"
csv_path = base / f"{name}.csv"
jsonl_path = base / f"{name}.jsonl"
sft_path = base / f"{name}.sft.jsonl"

print("1. CSV → JSONL")
n_jsonl = convert_csv_to_jsonl(csv_path, jsonl_path)
print("JSONL 레코드:", n_jsonl)

print("\n2. JSONL → SFT")
n_sft, _ = convert_jsonl_to_sft(jsonl_path, sft_path)
print("SFT 레코드:", n_sft)
