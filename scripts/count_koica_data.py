#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""KOICA 데이터 파일들의 라인 수와 크기를 집계합니다."""

import os
import sys
from pathlib import Path

# 프로젝트 루트로 이동
script_path = Path(__file__).resolve()
project_root = script_path.parent.parent
data_dir = project_root / "data" / "koica_data"

if not data_dir.exists():
    print(f"ERROR: 데이터 디렉토리를 찾을 수 없습니다: {data_dir}")
    print(f"현재 스크립트 위치: {script_path}")
    print(f"프로젝트 루트: {project_root}")
    sys.exit(1)

# 파일 경로를 절대 경로로 변환
data_dir = data_dir.resolve()

# 확인할 파일 목록
files = [
    "koica_data_train.jsonl",
    "koica_data_val.jsonl",
    "koica_data_test.jsonl",
    "한국국제협력단_조달계약 규정 안내 서비스 질의응답 세트_20251031.sft.jsonl",
    "한국국제협력단_민관협력사업 사업개요_20221222.sft.jsonl",
    "한국국제협력단_국제기구 협력사업 목록_20251231.sft.jsonl",
    "한국국제협력단_국별협력 진행사업 목록_20251231.sft.jsonl",
    "한국국제협력단_ODA 용어사전_20230612.sft.jsonl",
]

print("=" * 70)
print("KOICA 훈련 데이터 통계")
print("=" * 70)
print()

total_lines = 0
train_lines = 0
val_lines = 0
test_lines = 0
sft_lines = 0

for filename in files:
    filepath = data_dir / filename
    if filepath.exists():
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                lines = sum(1 for _ in f)
            size = filepath.stat().st_size
            total_lines += lines
            
            if "train" in filename:
                train_lines += lines
            elif "val" in filename:
                val_lines += lines
            elif "test" in filename:
                test_lines += lines
            elif ".sft.jsonl" in filename:
                sft_lines += lines
            
            print(f"{filename}")
            print(f"  - 라인 수: {lines:,} lines")
            print(f"  - 파일 크기: {size/1024:.1f} KB ({size/1024/1024:.2f} MB)")
            print()
        except Exception as e:
            print(f"{filename}: 읽기 실패 - {e}")
            print()

print("=" * 70)
print("요약")
print("=" * 70)
print(f"Train 데이터:       {train_lines:,} lines")
print(f"Validation 데이터:  {val_lines:,} lines")
print(f"Test 데이터:        {test_lines:,} lines")
print(f"SFT 데이터:         {sft_lines:,} lines")
print(f"{'-' * 70}")
print(f"총 훈련 가능 데이터: {total_lines:,} lines ({total_lines/1000:.1f}K samples)")
train_total = train_lines + sft_lines
print(f"실제 Train 전용:    {train_total:,} lines ({train_total/1000:.1f}K samples)")
print("=" * 70)
