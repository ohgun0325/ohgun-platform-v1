"""CUDA 및 GPU 환경 확인 스크립트"""

import sys
import subprocess
from pathlib import Path
import os

# OpenMP 라이브러리 중복 문제 해결
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

# Windows 콘솔 인코딩 설정
if sys.platform == "win32":
    os.system("chcp 65001 >nul 2>&1")

print("=" * 60)
print("CUDA 및 GPU 환경 확인")
print("=" * 60)
print()

# 1. NVIDIA 드라이버 확인
print("[1] NVIDIA 드라이버 확인")
print("-" * 60)
try:
    result = subprocess.run(
        ["nvidia-smi"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="ignore"
    )
    if result.returncode == 0:
        print("[OK] NVIDIA 드라이버가 설치되어 있습니다.")
        # GPU 정보 추출
        lines = result.stdout.split("\n")
        for line in lines:
            if "CUDA Version" in line:
                print(f"   {line.strip()}")
            elif "GeForce" in line or "RTX" in line or "GTX" in line:
                gpu_info = line.split("|")[1].strip() if "|" in line else line.strip()
                print(f"   GPU: {gpu_info}")
            elif "MiB /" in line and "Memory-Usage" not in line:
                memory_info = line.split("|")[2].strip() if "|" in line else line.strip()
                print(f"   메모리: {memory_info}")
    else:
        print("[ERROR] NVIDIA 드라이버를 찾을 수 없습니다.")
except FileNotFoundError:
    print("[ERROR] nvidia-smi 명령어를 찾을 수 없습니다.")
    print("   NVIDIA 드라이버가 설치되어 있지 않을 수 있습니다.")
except Exception as e:
    print(f"[WARNING] 오류 발생: {e}")

print()

# 2. PyTorch 설치 확인
print("[2] PyTorch 설치 확인")
print("-" * 60)
try:
    import torch
    print(f"[OK] PyTorch가 설치되어 있습니다.")
    print(f"   버전: {torch.__version__}")
    
    # CUDA 사용 가능 여부
    print()
    print("[3] CUDA 사용 가능 여부")
    print("-" * 60)
    if torch.cuda.is_available():
        print("[OK] CUDA를 사용할 수 있습니다!")
        print(f"   CUDA 버전: {torch.version.cuda}")
        print(f"   cuDNN 버전: {torch.backends.cudnn.version() if torch.backends.cudnn.is_available() else 'N/A'}")
        print(f"   GPU 개수: {torch.cuda.device_count()}")
        
        for i in range(torch.cuda.device_count()):
            print(f"\n   GPU {i}:")
            print(f"      이름: {torch.cuda.get_device_name(i)}")
            print(f"      메모리: {torch.cuda.get_device_properties(i).total_memory / 1024**3:.2f} GB")
            print(f"      계산 능력: {torch.cuda.get_device_properties(i).major}.{torch.cuda.get_device_properties(i).minor}")
    else:
        print("[ERROR] CUDA를 사용할 수 없습니다.")
        print("   가능한 원인:")
        print("   1. PyTorch가 CPU 버전으로 설치됨")
        print("   2. CUDA 버전이 PyTorch와 호환되지 않음")
        print("   3. GPU 드라이버가 설치되지 않음")
        
except ImportError:
    print("[ERROR] PyTorch가 설치되어 있지 않습니다.")
    print("   설치 방법:")
    print("   - CPU 버전: pip install torch")
    print("   - CUDA 11.8: pip install torch --index-url https://download.pytorch.org/whl/cu118")
    print("   - CUDA 12.1: pip install torch --index-url https://download.pytorch.org/whl/cu121")
except Exception as e:
    print(f"⚠️  오류 발생: {e}")

print()

# 3. 필요한 패키지 확인
print("[4] 필요한 패키지 확인")
print("-" * 60)
required_packages = {
    "torch": "PyTorch",
    "transformers": "Transformers",
    "peft": "PEFT (LoRA)",
    "bitsandbytes": "BitsAndBytes (4-bit 양자화)",
    "trl": "TRL (SFTTrainer)",
    "datasets": "HuggingFace Datasets",
}

for package, description in required_packages.items():
    try:
        mod = __import__(package)
        version = getattr(mod, "__version__", "unknown")
        print(f"[OK] {description}: {version}")
    except ImportError:
        print(f"[ERROR] {description}: 설치되지 않음")

print()

# 4. 권장 사항
print("[5] 권장 사항")
print("-" * 60)

try:
    import torch
    if torch.cuda.is_available():
        gpu_memory = torch.cuda.get_device_properties(0).total_memory / 1024**3
        print("[OK] GPU 환경이 준비되어 있습니다!")
        print(f"   GPU 메모리: {gpu_memory:.2f} GB")
        
        if gpu_memory >= 16:
            print("   권장 배치 크기: 4-8")
        elif gpu_memory >= 12:
            print("   권장 배치 크기: 2-4")
        elif gpu_memory >= 8:
            print("   권장 배치 크기: 1-2 (4-bit 양자화 필수)")
        else:
            print("   [WARNING] GPU 메모리가 부족할 수 있습니다.")
            print("   4-bit 양자화를 사용하세요.")
    else:
        print("[WARNING] CUDA를 사용할 수 없습니다.")
        print("   GPU 훈련을 위해서는 CUDA 버전의 PyTorch가 필요합니다.")
except:
    print("[WARNING] PyTorch가 설치되지 않아 GPU 정보를 확인할 수 없습니다.")

print()
print("=" * 60)
