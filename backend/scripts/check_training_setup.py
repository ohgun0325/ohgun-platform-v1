"""훈련 환경 확인 스크립트

GPU 사용 가능 여부, QLoRA 설정, 필요한 패키지 설치 여부를 확인합니다.
"""

import sys
from pathlib import Path

# kr 모듈 루트를 경로에 추가 (domain 등 import 해결용)
project_root = Path(__file__).parent.parent
kr_root = project_root / "api" / "ohgun" / "kr"
sys.path.insert(0, str(kr_root))

import os

# OpenMP 라이브러리 중복 문제 해결 (가장 먼저 설정)
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import torch


def check_cuda():
    """CUDA 사용 가능 여부 확인"""
    print("=" * 60)
    print("1. CUDA 확인")
    print("=" * 60)
    
    cuda_available = torch.cuda.is_available()
    print(f"CUDA 사용 가능: {cuda_available}")
    
    if cuda_available:
        print(f"CUDA 버전: {torch.version.cuda}")
        print(f"cuDNN 버전: {torch.backends.cudnn.version()}")
        print(f"GPU 개수: {torch.cuda.device_count()}")
        
        for i in range(torch.cuda.device_count()):
            print(f"\nGPU {i}: {torch.cuda.get_device_name(i)}")
            print(f"  메모리: {torch.cuda.get_device_properties(i).total_memory / 1024**3:.2f} GB")
            print(f"  할당된 메모리: {torch.cuda.memory_allocated(i) / 1024**3:.2f} GB")
            print(f"  캐시된 메모리: {torch.cuda.memory_reserved(i) / 1024**3:.2f} GB")
    else:
        print("[WARNING] CUDA를 사용할 수 없습니다. CPU로 훈련하면 매우 느립니다.")
    
    print()
    return cuda_available


def check_packages():
    """필요한 패키지 설치 여부 확인"""
    print("=" * 60)
    print("2. 필수 패키지 확인")
    print("=" * 60)
    
    packages = {
        "torch": "PyTorch",
        "transformers": "Transformers",
        "peft": "PEFT (LoRA)",
        "bitsandbytes": "BitsAndBytes (4-bit 양자화)",
        "trl": "TRL (SFTTrainer)",
        "datasets": "Datasets",
    }
    
    missing = []
    for package, name in packages.items():
        try:
            if package == "torch":
                import torch
                version = torch.__version__
            elif package == "transformers":
                import transformers
                version = transformers.__version__
            elif package == "peft":
                import peft
                version = peft.__version__
            elif package == "bitsandbytes":
                import bitsandbytes
                version = bitsandbytes.__version__
            elif package == "trl":
                import trl
                version = trl.__version__
            elif package == "datasets":
                import datasets
                version = datasets.__version__
            
            print(f"[OK] {name}: {version}")
        except ImportError:
            print(f"[MISSING] {name}: 설치되지 않음")
            missing.append(package)
    
    print()
    if missing:
        print(f"[WARNING] 다음 패키지가 설치되지 않았습니다: {', '.join(missing)}")
        print("설치 명령어: pip install " + " ".join(missing))
    else:
        print("[OK] 모든 필수 패키지가 설치되어 있습니다.")
    
    print()
    return len(missing) == 0


def check_bitsandbytes():
    """BitsAndBytes가 CUDA를 지원하는지 확인"""
    print("=" * 60)
    print("3. BitsAndBytes CUDA 지원 확인")
    print("=" * 60)
    
    try:
        import bitsandbytes as bnb
        from bitsandbytes import functional as F
        
        # CUDA 지원 여부 확인
        if torch.cuda.is_available():
            try:
                # 간단한 테스트
                test_tensor = torch.randn(10, 10).cuda()
                quantized = bnb.nn.Linear4bit(10, 10).cuda()
                print("[OK] BitsAndBytes가 CUDA를 지원합니다.")
                print("[OK] 4-bit 양자화 사용 가능")
                return True
            except Exception as e:
                print(f"[ERROR] BitsAndBytes CUDA 테스트 실패: {e}")
                return False
        else:
            print("[WARNING] CUDA를 사용할 수 없어 BitsAndBytes를 테스트할 수 없습니다.")
            return False
    except ImportError:
        print("[ERROR] BitsAndBytes가 설치되지 않았습니다.")
        return False
    except Exception as e:
        print(f"[ERROR] BitsAndBytes 확인 중 오류: {e}")
        return False
    
    print()


def check_exaone_model():
    """Exaone 모델 파일 존재 여부 확인"""
    print("=" * 60)
    print("4. Exaone 모델 파일 확인")
    print("=" * 60)
    
    project_root = Path(__file__).parent.parent
    model_path = project_root / "models" / "exaone-2.4b"
    
    if not model_path.exists():
        print(f"[ERROR] 모델 경로를 찾을 수 없습니다: {model_path}")
        return False
    
    required_files = [
        "config.json",
        "tokenizer.json",
        "model.safetensors.index.json",
        "modeling_exaone.py",
    ]
    
    missing_files = []
    for file in required_files:
        file_path = model_path / file
        if file_path.exists():
            size = file_path.stat().st_size / (1024**2)  # MB
            print(f"[OK] {file} ({size:.1f} MB)")
        else:
            print(f"[MISSING] {file}")
            missing_files.append(file)
    
    # safetensors 파일 확인
    safetensors_files = list(model_path.glob("model-*.safetensors"))
    if safetensors_files:
        total_size = sum(f.stat().st_size for f in safetensors_files) / (1024**3)  # GB
        print(f"[OK] Safetensors 파일: {len(safetensors_files)}개 (총 {total_size:.2f} GB)")
    else:
        print("[MISSING] Safetensors 파일을 찾을 수 없습니다.")
        missing_files.append("model-*.safetensors")
    
    print()
    if missing_files:
        print(f"[ERROR] 다음 파일이 없습니다: {', '.join(missing_files)}")
        return False
    else:
        print("[OK] 모든 모델 파일이 존재합니다.")
    
    print()
    return True


def check_training_data():
    """훈련 데이터 확인"""
    print("=" * 60)
    print("5. 훈련 데이터 확인")
    print("=" * 60)
    
    project_root = Path(__file__).parent.parent
    koica_data_dir = project_root / "data" / "koica_data"
    
    train_file = koica_data_dir / "koica_data_train.jsonl"
    val_file = koica_data_dir / "koica_data_val.jsonl"
    test_file = koica_data_dir / "koica_data_test.jsonl"
    
    files = {
        "Train": train_file,
        "Val": val_file,
        "Test": test_file,
    }
    
    all_exist = True
    for name, file_path in files.items():
        if file_path.exists():
            # 라인 수 계산
            with open(file_path, 'r', encoding='utf-8') as f:
                line_count = sum(1 for _ in f)
            size = file_path.stat().st_size / (1024**2)  # MB
            print(f"[OK] {name}: {line_count:,}개 레코드 ({size:.1f} MB)")
        else:
            print(f"[MISSING] {name}: {file_path.name}")
            all_exist = False
    
    print()
    if not all_exist:
        print("[WARNING] 일부 데이터 파일이 없습니다.")
        print("먼저 scripts/prepare_koica_data.py를 실행하여 데이터를 준비하세요.")
    else:
        print("[OK] 모든 훈련 데이터가 준비되어 있습니다.")
    
    print()
    return all_exist


def test_model_loading():
    """모델 로드 테스트 (실제 GPU 사용 확인)"""
    print("=" * 60)
    print("6. 모델 로드 테스트 (GPU 사용 확인)")
    print("=" * 60)
    
    if not torch.cuda.is_available():
        print("[SKIP] CUDA를 사용할 수 없어 모델 로드 테스트를 건너뜁니다.")
        return False
    
    try:
        from domain.shared.services.exaone_trainer import ExaoneTrainer
        
        project_root = Path(__file__).parent.parent
        model_path = project_root / "models" / "exaone-2.4b"
        
        print("ExaoneTrainer 초기화 중...")
        trainer = ExaoneTrainer(
            model_path=str(model_path),
            output_dir="models/test-output",
            use_4bit=True,
            device_map="auto",
            torch_dtype="float16",
        )
        
        print("모델 로드 중... (이 작업은 몇 분 걸릴 수 있습니다)")
        trainer.load_model()
        
        # 모델이 GPU에 있는지 확인
        if hasattr(trainer.model, 'device'):
            device = trainer.model.device
        else:
            # device_map="auto"를 사용한 경우
            device = next(trainer.model.parameters()).device
        
        print(f"[OK] 모델이 로드되었습니다.")
        print(f"[OK] 모델 디바이스: {device}")
        
        if device.type == 'cuda':
            print(f"[OK] GPU 사용 중: {torch.cuda.get_device_name(device.index)}")
            print(f"[OK] GPU 메모리 사용량: {torch.cuda.memory_allocated(device.index) / 1024**3:.2f} GB")
        else:
            print("[WARNING] 모델이 CPU에 로드되었습니다.")
        
        # QLoRA 확인
        if trainer.peft_model is not None:
            print("[OK] QLoRA (PEFT) 모델이 적용되었습니다.")
            trainer.peft_model.print_trainable_parameters()
        else:
            print("[WARNING] QLoRA 모델이 적용되지 않았습니다.")
        
        # 정리
        trainer.unload()
        print("[OK] 모델 언로드 완료")
        
        print()
        return True
        
    except Exception as e:
        print(f"[ERROR] 모델 로드 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        print()
        return False


def main():
    """메인 함수"""
    print("=" * 60)
    print("Exaone 훈련 환경 확인")
    print("=" * 60)
    print()
    
    results = {
        "CUDA": check_cuda(),
        "패키지": check_packages(),
        "BitsAndBytes": check_bitsandbytes() if torch.cuda.is_available() else None,
        "모델 파일": check_exaone_model(),
        "훈련 데이터": check_training_data(),
    }
    
    # 모델 로드 테스트 실행 (자동)
    print("=" * 60)
    print("6. 모델 로드 테스트 (GPU 및 QLoRA 확인)")
    print("=" * 60)
    print("모델 로드를 테스트합니다. (시간이 걸릴 수 있습니다)")
    print()
    
    try:
        results["모델 로드"] = test_model_loading()
    except Exception as e:
        print(f"[ERROR] 모델 로드 테스트 실패: {e}")
        results["모델 로드"] = False
    
    # 최종 요약
    print("=" * 60)
    print("확인 결과 요약")
    print("=" * 60)
    
    for name, result in results.items():
        if result is None:
            status = "[SKIP]"
        elif result:
            status = "[OK]"
        else:
            status = "[FAIL]"
        print(f"{status} {name}")
    
    print()
    
    # 훈련 가능 여부 판단
    critical_checks = ["CUDA", "패키지", "모델 파일", "훈련 데이터"]
    can_train = all(results.get(check, False) for check in critical_checks)
    
    if can_train:
        print("=" * 60)
        print("[OK] 훈련을 시작할 수 있습니다!")
        print("=" * 60)
        print()
        print("훈련 실행 명령어:")
        print("  python scripts/train_exaone_koica.py")
        print()
    else:
        print("=" * 60)
        print("[WARNING] 일부 확인 항목이 실패했습니다.")
        print("=" * 60)
        print()
        print("위의 오류를 해결한 후 다시 확인하세요.")
        print()
    
    print("=" * 60)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[WARNING] 사용자에 의해 중단되었습니다.")
    except Exception as e:
        print(f"\n\n[ERROR] 오류 발생: {e}")
        import traceback
        traceback.print_exc()
