"""labels가 제대로 생성되는지 확인하는 스크립트"""

import json
import sys
from pathlib import Path

# kr 모듈 루트를 Python 경로에 추가 (domain 등 import 해결용)
project_root = Path(__file__).parent.absolute()
kr_root = project_root / "api" / "ohgun" / "kr"
if str(kr_root) not in sys.path:
    sys.path.insert(0, str(kr_root))

from domain.shared.services.sft_dataset_builder import build_dataset_dict

# 데이터 로드
project_root = Path(__file__).parent
data_dir = project_root / "data"
dataset_dict = build_dataset_dict(data_dir)

# 샘플 데이터 확인
print("=== Train 데이터 샘플 ===")
for i in range(min(5, len(dataset_dict["train"]))):
    sample = dataset_dict["train"][i]
    print(f"\n샘플 {i+1}:")
    print(f"  instruction: {sample.get('instruction', 'N/A')[:100]}...")
    print(f"  input: {sample.get('input', 'N/A')}")
    print(f"  output: {sample.get('output', 'N/A')}")
    
    # output 파싱
    output_str = sample.get("output", "{}")
    try:
        if isinstance(output_str, str):
            output_dict = json.loads(output_str)
        else:
            output_dict = output_str
        
        action = output_dict.get("action", "ALLOW")
        label = 1 if action == "BLOCK" else 0
        print(f"  -> action: {action}, label: {label}")
    except Exception as e:
        print(f"  -> 파싱 실패: {e}")

# 전체 데이터의 label 분포 확인
print("\n=== Label 분포 확인 ===")
label_counts = {"BLOCK": 0, "ALLOW": 0, "ERROR": 0}
for sample in dataset_dict["train"]:
    output_str = sample.get("output", "{}")
    try:
        if isinstance(output_str, str):
            output_dict = json.loads(output_str)
        else:
            output_dict = output_str
        
        action = output_dict.get("action", "ALLOW")
        if action == "BLOCK":
            label_counts["BLOCK"] += 1
        elif action == "ALLOW":
            label_counts["ALLOW"] += 1
        else:
            label_counts["ERROR"] += 1
    except Exception as e:
        label_counts["ERROR"] += 1

print(f"BLOCK (1): {label_counts['BLOCK']:,}개")
print(f"ALLOW (0): {label_counts['ALLOW']:,}개")
print(f"ERROR: {label_counts['ERROR']:,}개")
print(f"총계: {sum(label_counts.values()):,}개")
