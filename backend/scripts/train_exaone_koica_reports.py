"""Exaone 모델 훈련 스크립트 (KOICA 보고서 요약용)

KOICA 평가보고서 SFT 데이터(koica_reports_train/val/test.jsonl)로
Exaone을 fine-tuning하여 보고서 내용 요약 능력을 학습시킵니다.

사용법:
    python scripts/train_exaone_koica_reports.py

사전 조건:
  - 1단계: scripts/koica_reports_to_sft.py 실행 → koica_reports.sft.jsonl
  - 2단계: scripts/split_koica_reports_sft.py 실행 → train/val/test 분할
  - models/exaone-2.4b 모델 다운로드 완료
"""

import os

# OpenMP 라이브러리 중복 문제 해결 (가장 먼저 설정)
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import sys
from pathlib import Path

# kr 모듈 루트를 경로에 추가 (domain 등 import 해결용)
project_root = Path(__file__).resolve().parent.parent
kr_root = project_root / "api" / "ohgun" / "kr"
sys.path.insert(0, str(kr_root))

from domain.shared.services.exaone_trainer import ExaoneTrainer


def main():
    """Exaone 모델 훈련 메인 함수 (KOICA 보고서 요약)"""
    print("=" * 60)
    print("Exaone 모델 훈련 (KOICA 보고서 요약)")
    print("=" * 60)
    print()

    # 경로 설정
    model_path = project_root / "models" / "exaone-2.4b"
    reports_dir = project_root / "data" / "koica_reports"

    train_file = reports_dir / "koica_reports_train.jsonl"
    val_file = reports_dir / "koica_reports_val.jsonl"
    test_file = reports_dir / "koica_reports_test.jsonl"

    if not train_file.exists():
        raise FileNotFoundError(
            f"훈련 데이터를 찾을 수 없습니다: {train_file}\n"
            "먼저 1단계(koica_reports_to_sft.py), 2단계(split_koica_reports_sft.py)를 실행하세요."
        )

    # ExaoneTrainer 초기화 (보고서 요약용 출력 디렉터리)
    trainer = ExaoneTrainer(
        model_path=str(model_path),
        output_dir=str(project_root / "models" / "exaone-koica-reports"),
        use_4bit=True,
        device_map="auto",
        torch_dtype="float16",
        use_fp16_training=False,
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

    # 보고서 페이지는 텍스트가 길 수 있음 → max_seq_length 1024
    max_seq_length = 1024
    num_epochs = 3
    batch_size = 4
    save_steps = max(20, len(training_data) // (batch_size * 2))  # 77건 기준 약 20

    print()
    print("=" * 60)
    print("훈련 설정")
    print("=" * 60)
    print(f"훈련 샘플: {len(training_data):,}개")
    print(f"평가 샘플: {len(eval_data):,}개" if eval_data else "평가 샘플: 없음")
    print(f"에포크: {num_epochs}")
    print(f"배치 크기: {batch_size}")
    print(f"학습률: 2e-4")
    print(f"최대 시퀀스 길이: {max_seq_length}")
    print(f"저장 간격: {save_steps} steps")
    print("=" * 60)
    print()

    output_path = trainer.train(
        training_data=training_data,
        eval_data=eval_data,
        num_epochs=num_epochs,
        batch_size=batch_size,
        learning_rate=2e-4,
        max_seq_length=max_seq_length,
        save_steps=save_steps,
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
    print("  - 추론 시 위 경로의 LoRA 어댑터를 로드하여 보고서 요약 테스트")
    print("=" * 60)

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
