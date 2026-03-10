"""KOICA 데이터를 훈련 가능한 구조로 변환하는 통합 스크립트.

koreapost_spem 구조를 참고하여 다음 단계를 수행합니다:
1. CSV → JSONL 변환
2. JSONL → SFT JSONL 변환
3. SFT JSONL → train/val/test 분할
"""

import os
# OpenMP 라이브러리 중복 문제 해결 (가장 먼저 설정)
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import sys
from pathlib import Path

# 프로젝트 루트를 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.domain.shared.services.convert_koica_to_jsonl import main as convert_jsonl
from app.domain.shared.services.convert_koica_to_sft import main as convert_sft
from app.domain.shared.services.split_koica_dataset import main as split_dataset


def main():
    """전체 변환 프로세스 실행"""
    print("=" * 60)
    print("KOICA 데이터 훈련 준비 프로세스")
    print("=" * 60)
    print()
    
    # Step 1: CSV → JSONL
    print("[Step 1/3] CSV → JSONL 변환")
    print("-" * 60)
    try:
        convert_jsonl()
        print("✅ Step 1 완료\n")
    except Exception as e:
        print(f"❌ Step 1 실패: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Step 2: JSONL → SFT JSONL
    print("[Step 2/3] JSONL → SFT JSONL 변환")
    print("-" * 60)
    try:
        convert_sft()
        print("✅ Step 2 완료\n")
    except Exception as e:
        print(f"❌ Step 2 실패: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Step 3: SFT JSONL → train/val/test 분할
    print("[Step 3/3] SFT JSONL → train/val/test 분할")
    print("-" * 60)
    try:
        split_dataset()
        print("✅ Step 3 완료\n")
    except Exception as e:
        print(f"❌ Step 3 실패: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print("=" * 60)
    print("✅ 모든 변환 작업 완료!")
    print("=" * 60)
    print()
    print("생성된 파일:")
    print("  - data/koica_data/*.jsonl (원본 JSONL)")
    print("  - data/koica_data/*.sft.jsonl (SFT 형식)")
    print("  - data/koica_data/koica_data_train.jsonl")
    print("  - data/koica_data/koica_data_val.jsonl")
    print("  - data/koica_data/koica_data_test.jsonl")
    print()
    print("다음 단계:")
    print("  python scripts/train_exaone.py  # Exaone 모델 훈련")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  사용자에 의해 중단되었습니다.")
    except Exception as e:
        print(f"\n\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
