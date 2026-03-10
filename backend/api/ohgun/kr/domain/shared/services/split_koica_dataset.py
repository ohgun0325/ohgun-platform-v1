"""KOICA SFT 데이터셋을 Train/Val/Test로 분할하는 스크립트."""

import json
import random
from pathlib import Path
from typing import List, Dict, Any


def load_sft_jsonl(file_path: Path) -> List[Dict[str, Any]]:
    """SFT JSONL 파일을 로드합니다.
    
    Args:
        file_path: JSONL 파일 경로
        
    Returns:
        JSONL 데이터 리스트
    """
    data = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                data.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return data


def save_jsonl(data: List[Dict[str, Any]], output_path: Path) -> None:
    """데이터를 JSONL 파일로 저장합니다.
    
    Args:
        data: 저장할 데이터 리스트
        output_path: 출력 파일 경로
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        for item in data:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')


def split_dataset(
    data: List[Dict[str, Any]],
    train_ratio: float = 0.8,
    val_ratio: float = 0.1,
    test_ratio: float = 0.1,
    random_seed: int = 42,
) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """데이터셋을 Train/Val/Test로 분할합니다.
    
    Args:
        data: 분할할 데이터 리스트
        train_ratio: 학습 데이터 비율 (기본: 0.8)
        val_ratio: 검증 데이터 비율 (기본: 0.1)
        test_ratio: 테스트 데이터 비율 (기본: 0.1)
        random_seed: 랜덤 시드 (재현성 보장)
        
    Returns:
        (train_data, val_data, test_data) 튜플
    """
    # 비율 검증
    total_ratio = train_ratio + val_ratio + test_ratio
    if abs(total_ratio - 1.0) > 0.001:
        raise ValueError(f"비율의 합이 1.0이어야 합니다. 현재: {total_ratio}")
    
    print(f"\n데이터셋 분할 시작...")
    print(f"총 레코드: {len(data):,}개")
    print(f"분할 비율: Train {train_ratio*100:.0f}% / Val {val_ratio*100:.0f}% / Test {test_ratio*100:.0f}%")
    
    # 랜덤 시드 설정
    random.seed(random_seed)
    
    # 데이터 셔플
    shuffled_data = data.copy()
    random.shuffle(shuffled_data)
    
    # 분할 인덱스 계산
    total = len(shuffled_data)
    train_end = int(total * train_ratio)
    val_end = train_end + int(total * val_ratio)
    
    # 분할
    train_data = shuffled_data[:train_end]
    val_data = shuffled_data[train_end:val_end]
    test_data = shuffled_data[val_end:]
    
    print(f"\n분할 완료:")
    print(f"  Train: {len(train_data):,}개 ({len(train_data)/total*100:.1f}%)")
    print(f"  Val:   {len(val_data):,}개 ({len(val_data)/total*100:.1f}%)")
    print(f"  Test:  {len(test_data):,}개 ({len(test_data)/total*100:.1f}%)")
    
    return train_data, val_data, test_data


def merge_all_sft_files(koica_data_dir: Path) -> List[Dict[str, Any]]:
    """모든 SFT JSONL 파일을 하나로 합칩니다.
    
    Args:
        koica_data_dir: koica_data 디렉토리 경로
        
    Returns:
        합쳐진 데이터 리스트
    """
    sft_files = sorted(koica_data_dir.glob("*.sft.jsonl"))
    
    if not sft_files:
        raise FileNotFoundError(f"SFT JSONL 파일을 찾을 수 없습니다: {koica_data_dir}")
    
    print(f"총 {len(sft_files)}개의 SFT 파일을 찾았습니다.\n")
    
    all_data = []
    for sft_file in sft_files:
        print(f"로드 중: {sft_file.name}")
        data = load_sft_jsonl(sft_file)
        all_data.extend(data)
        print(f"  {len(data):,}개 레코드 추가")
    
    print(f"\n[OK] 전체 {len(all_data):,}개 레코드 통합 완료")
    return all_data


def main():
    """메인 함수: 모든 KOICA SFT 파일을 합쳐서 train/val/test로 분할합니다."""
    project_root = Path(__file__).parent.parent.parent
    koica_data_dir = project_root / "data" / "koica_data"
    
    if not koica_data_dir.exists():
        print(f"[ERROR] 디렉토리를 찾을 수 없습니다: {koica_data_dir}")
        return
    
    print("=" * 60)
    print("KOICA 데이터셋 Train/Val/Test 분할")
    print("=" * 60)
    print(f"데이터 폴더: {koica_data_dir}\n")
    
    try:
        # 모든 SFT 파일 통합
        all_data = merge_all_sft_files(koica_data_dir)
        
        if not all_data:
            print("[WARNING] 통합할 데이터가 없습니다.")
            return
        
        # 분할
        train_data, val_data, test_data = split_dataset(
            all_data,
            train_ratio=0.8,
            val_ratio=0.1,
            test_ratio=0.1,
            random_seed=42,
        )
        
        # 저장
        train_path = koica_data_dir / "koica_data_train.jsonl"
        val_path = koica_data_dir / "koica_data_val.jsonl"
        test_path = koica_data_dir / "koica_data_test.jsonl"
        
        print(f"\n파일 저장 중...")
        save_jsonl(train_data, train_path)
        save_jsonl(val_data, val_path)
        save_jsonl(test_data, test_path)
        
        print("\n" + "=" * 60)
        print("데이터셋 분할 및 저장 완료!")
        print("=" * 60)
        print(f"Train: {train_path.name} ({len(train_data):,}개)")
        print(f"Val:   {val_path.name} ({len(val_data):,}개)")
        print(f"Test:  {test_path.name} ({len(test_data):,}개)")
        print("=" * 60)
        
    except Exception as e:
        print(f"[ERROR] 오류 발생: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
