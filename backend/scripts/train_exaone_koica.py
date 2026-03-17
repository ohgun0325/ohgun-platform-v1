"""Exaone 모델 훈련 스크립트 (KOICA 데이터용)

사용법:
    python scripts/train_exaone_koica.py
"""

import os
# OpenMP 라이브러리 중복 문제 해결 (가장 먼저 설정)
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import sys
from pathlib import Path

# kr 모듈 루트를 경로에 추가 (domain 등 import 해결용)
project_root = Path(__file__).parent.parent
kr_root = project_root / "api" / "ohgun" / "kr"
sys.path.insert(0, str(kr_root))

from domain.shared.services.exaone_trainer import ExaoneTrainer


def main():
    """Exaone 모델 훈련 메인 함수 (KOICA 데이터)"""
    print("=" * 60)
    print("Exaone 모델 훈련 스크립트 (KOICA 데이터)")
    print("=" * 60)
    print()
    
    # 경로 설정
    project_root = Path(__file__).parent.parent
    model_path = project_root / "models" / "exaone-2.4b"
    koica_data_dir = project_root / "data" / "koica_data"
    
    # 훈련 데이터 로드
    train_file = koica_data_dir / "koica_data_train.jsonl"
    val_file = koica_data_dir / "koica_data_val.jsonl"
    test_file = koica_data_dir / "koica_data_test.jsonl"
    
    if not train_file.exists():
        raise FileNotFoundError(
            f"훈련 데이터를 찾을 수 없습니다: {train_file}\n"
            f"먼저 scripts/prepare_koica_data.py를 실행하여 데이터를 준비하세요."
        )
    
    # ExaoneTrainer 초기화
    trainer = ExaoneTrainer(
        model_path=str(model_path),
        output_dir="models/exaone-koica-classifier",
        use_4bit=True,
        device_map="auto",
        torch_dtype="float16",
        use_fp16_training=False,  # BFloat16 에러 방지를 위해 FP16 Mixed Precision 비활성화
    )
    
    # 모델 로드
    trainer.load_model()
    
    # 데이터 로드
    print()
    print("=" * 60)
    print("데이터 로드 중...")
    print("=" * 60)
    training_data = trainer.load_jsonl_data(str(train_file))
    
    eval_data = None
    if val_file.exists():
        eval_data = trainer.load_jsonl_data(str(val_file))
        print(f"평가 데이터: {len(eval_data):,}개 레코드")
    
    # 훈련 실행
    print()
    print("=" * 60)
    print("훈련 설정")
    print("=" * 60)
    print(f"훈련 샘플: {len(training_data):,}개")
    print(f"평가 샘플: {len(eval_data):,}개" if eval_data else "평가 샘플: 없음")
    print(f"에포크: 3")
    print(f"배치 크기: 4")
    print(f"학습률: 2e-4")
    print(f"최대 시퀀스 길이: 512")
    print("=" * 60)
    print()
    
    output_path = trainer.train(
        training_data=training_data,
        eval_data=eval_data,
        num_epochs=3,
        batch_size=4,
        learning_rate=2e-4,
        max_seq_length=512,
        save_steps=100,  # KOICA 데이터가 적으므로 더 자주 저장
        logging_steps=10,
    )
    
    print()
    print("=" * 60)
    print("훈련 완료!")
    print("=" * 60)
    print(f"모델 저장 위치: {output_path}")
    print()
    print("생성된 파일:")
    print(f"  - {output_path}/adapter_model.safetensors (LoRA 어댑터)")
    print(f"  - {output_path}/adapter_config.json (LoRA 설정)")
    print(f"  - {output_path}/tokenizer files (토크나이저)")
    print()
    print("다음 단계:")
    print("1. 모델 테스트: python scripts/test_exaone_koica.py")
    print("2. 모델 사용: app/models/exaone.py의 ExaoneLLM 클래스 사용")
    print("=" * 60)
    
    # 모델 언로드
    trainer.unload()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[WARNING] 사용자에 의해 중단되었습니다.")
    except Exception as e:
        print(f"\n\n[ERROR] 오류 발생: {e}")
        import traceback
        traceback.print_exc()
