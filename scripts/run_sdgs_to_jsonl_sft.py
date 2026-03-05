# -*- coding: utf-8 -*-
"""사업별 SDGs 연계 현황 CSV → JSONL → SFT 변환 (한글 경로)."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.domain.shared.services.convert_koica_to_jsonl import convert_csv_to_jsonl
from app.domain.shared.services.convert_koica_to_sft import convert_jsonl_to_sft

base = ROOT / "data" / "koica_data"
name = "한국국제협력단_사업별 지속가능개발목표(SDGs) 연계 현황_20231231"
csv_path = base / f"{name}.csv"
jsonl_path = base / f"{name}.jsonl"
sft_path = base / f"{name}.sft.jsonl"

print("1. CSV → JSONL")
n_jsonl = convert_csv_to_jsonl(csv_path, jsonl_path)
print("JSONL 레코드:", n_jsonl)

print("\n2. JSONL → SFT")
n_sft, _ = convert_jsonl_to_sft(jsonl_path, sft_path)
print("SFT 레코드:", n_sft)
