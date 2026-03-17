"""GPU 및 QLoRA 확인 테스트 스크립트"""

import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
kr_root = project_root / "api" / "ohgun" / "kr"
sys.path.insert(0, str(kr_root))

from domain.shared.services.exaone_trainer import ExaoneTrainer
import torch

print("=" * 60)
print("GPU 및 QLoRA 확인 테스트")
print("=" * 60)
print()

# CUDA 확인
print(f"CUDA 사용 가능: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"GPU: {torch.cuda.get_device_name(0)}")
    print(f"GPU 메모리: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.2f} GB")
print()

# 모델 로드
print("모델 로드 중...")
trainer = ExaoneTrainer(
    model_path="models/exaone-2.4b",
    output_dir="models/test-output",
    use_4bit=True,
    device_map="auto",
    torch_dtype="float16",
)

trainer.load_model()

# 디바이스 확인
device = next(trainer.model.parameters()).device
print()
print("=" * 60)
print("확인 결과")
print("=" * 60)
print(f"모델 디바이스: {device}")
print(f"GPU 사용: {device.type == 'cuda'}")
print(f"QLoRA 적용: {trainer.peft_model is not None}")

if trainer.peft_model:
    # 학습 가능 파라미터 계산
    trainable = sum(p.numel() for p in trainer.peft_model.parameters() if p.requires_grad)
    total = sum(p.numel() for p in trainer.peft_model.parameters())
    print(f"학습 가능 파라미터: {trainable:,}개 ({trainable/total*100:.2f}%)")
    print(f"전체 파라미터: {total:,}개")

if device.type == 'cuda':
    print(f"GPU 메모리 사용량: {torch.cuda.memory_allocated(device.index) / 1024**3:.2f} GB")
    print(f"GPU 메모리 캐시: {torch.cuda.memory_reserved(device.index) / 1024**3:.2f} GB")

print()
print("=" * 60)
if device.type == 'cuda' and trainer.peft_model:
    print("[OK] GPU로 실행되고 QLoRA가 적용되었습니다!")
    print("[OK] 훈련을 시작할 수 있습니다.")
else:
    print("[WARNING] GPU 또는 QLoRA 설정에 문제가 있습니다.")
print("=" * 60)

# 정리
trainer.unload()
