"""SFT 데이터셋(HuggingFace DatasetDict) 생성 스크립트.

- data/koreapost_spem_list_[train|val|test].jsonl 을 읽어 DatasetDict 로 변환
- 기본 분할 비율: Train/Val/Test = 80/10/10 (이미 분할된 파일 사용)
- 출력: 간단한 통계와 컬럼 구조
"""

from pathlib import Path
from typing import Dict

try:
    from datasets import Dataset, DatasetDict, load_dataset
except ModuleNotFoundError as e:
    raise SystemExit(
        "모듈 'datasets'가 없습니다. 아래 명령으로 설치 후 다시 실행하세요.\n"
        "pip install datasets"
    ) from e


def load_split_jsonl(data_dir: Path) -> Dict[str, str]:
    """Train/Val/Test JSONL 경로를 반환한다."""
    train_path = data_dir / "koreapost_spem_list_train.jsonl"
    val_path = data_dir / "koreapost_spem_list_val.jsonl"
    test_path = data_dir / "koreapost_spem_list_test.jsonl"

    for p in [train_path, val_path, test_path]:
        if not p.exists():
            raise FileNotFoundError(f"파일을 찾을 수 없습니다: {p}")

    return {
        "train": str(train_path),
        "validation": str(val_path),
        "test": str(test_path),
    }


def build_dataset_dict(data_dir: Path) -> DatasetDict:
    """JSONL 분할 파일을 HuggingFace DatasetDict로 로드한다."""
    split_files = load_split_jsonl(data_dir)

    # load_dataset은 split 인자를 통해 각각 로드 가능
    dataset = DatasetDict(
        {
            "train": load_dataset(
                "json", data_files=split_files["train"], split="train"
            ),
            "validation": load_dataset(
                "json", data_files=split_files["validation"], split="train"
            ),
            "test": load_dataset(
                "json", data_files=split_files["test"], split="train"
            ),
        }
    )
    return dataset


def print_stats(ds: DatasetDict) -> None:
    """데이터셋 간단 통계를 출력한다."""
    print("\n=== DatasetDict 생성 완료 ===")
    for split in ["train", "validation", "test"]:
        d: Dataset = ds[split]
        print(f"{split:<10} rows={len(d):>6}, columns={d.column_names}")
    print()


def main() -> None:
    project_root = Path(__file__).parent.parent.parent
    data_dir = project_root / "data"
    if not data_dir.exists():
        raise FileNotFoundError(f"data 디렉토리를 찾을 수 없습니다: {data_dir}")

    ds = build_dataset_dict(data_dir)
    print_stats(ds)


if __name__ == "__main__":
    main()
