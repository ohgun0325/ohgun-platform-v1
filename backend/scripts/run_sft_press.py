# -*- coding: utf-8 -*-
"""보도자료 JSONL → SFT 변환 (한글 경로)."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
kr_root = ROOT / "api" / "ohgun" / "kr"
sys.path.insert(0, str(kr_root))

from domain.shared.services.convert_koica_to_sft import convert_jsonl_to_sft

base = ROOT / "data" / "koica_data"
name = "한국국제협력단_개발협력 보도자료 정보_20251121"
n, _ = convert_jsonl_to_sft(base / f"{name}.jsonl", base / f"{name}.sft.jsonl")
print("SFT 레코드:", n)
