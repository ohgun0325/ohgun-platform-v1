"""스팸 메일 데이터셋 관리 Repository.

SFT JSONL 파일을 Train/Val/Test로 분할하는 기능을 제공합니다.
"""

import json
import random
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional


class SpamDatasetRepository:
    """스팸 메일 데이터셋 관리 클래스."""

    def __init__(self, data_dir: Optional[Path] = None):
        """Repository 초기화.

        Args:
            data_dir: 데이터 디렉토리 경로 (None이면 프로젝트 루트/data 사용)
        """
        if data_dir is None:
            # 프로젝트 루트 찾기 (이 파일이 app/repository/에 있으므로 2단계 위로)
            project_root = Path(__file__).parent.parent.parent
            data_dir = project_root / "data"
        
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def load_sft_jsonl(self, file_path: Optional[Path] = None) -> List[Dict[str, Any]]:
        """SFT JSONL 파일을 로드합니다.

        Args:
            file_path: JSONL 파일 경로 (None이면 data_dir에서 자동 찾기)

        Returns:
            JSONL 데이터 리스트
        """
        if file_path is None:
            # data 디렉토리에서 .sft.jsonl 파일 찾기
            sft_files = list(self.data_dir.glob("*.sft.jsonl"))
            if not sft_files:
                raise FileNotFoundError(
                    f"SFT JSONL 파일을 찾을 수 없습니다: {self.data_dir}"
                )
            file_path = sft_files[0]
            print(f"SFT 파일 자동 선택: {file_path.name}")

        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"파일을 찾을 수 없습니다: {file_path}")

        print(f"SFT JSONL 파일 로드 중: {file_path.name}")
        data = []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            for lineno, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    data.append(json.loads(line))
                except json.JSONDecodeError as e:
                    print(f"경고: {file_path.name}의 {lineno}번째 줄을 파싱할 수 없습니다: {e}")
                    continue

        print(f"총 {len(data):,}개 레코드 로드 완료")
        return data

    def split_dataset(
        self,
        data: List[Dict[str, Any]],
        train_ratio: float = 0.8,
        val_ratio: float = 0.1,
        test_ratio: float = 0.1,
        random_seed: int = 42,
        stratify: bool = False,
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
        """데이터셋을 Train/Val/Test로 분할합니다.

        Args:
            data: 분할할 데이터 리스트
            train_ratio: 학습 데이터 비율 (기본: 0.8)
            val_ratio: 검증 데이터 비율 (기본: 0.1)
            test_ratio: 테스트 데이터 비율 (기본: 0.1)
            random_seed: 랜덤 시드 (재현성 보장)
            stratify: Stratified split 사용 여부 (현재는 action 기반)

        Returns:
            (train_data, val_data, test_data) 튜플
        """
        # 비율 검증
        total_ratio = train_ratio + val_ratio + test_ratio
        if abs(total_ratio - 1.0) > 0.001:
            raise ValueError(
                f"비율의 합이 1.0이어야 합니다. 현재: {total_ratio}"
            )

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

    def save_jsonl(
        self,
        data: List[Dict[str, Any]],
        output_path: Path,
    ) -> None:
        """데이터를 JSONL 파일로 저장합니다.

        Args:
            data: 저장할 데이터 리스트
            output_path: 출력 파일 경로
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        print(f"JSONL 파일 저장 중: {output_path.name}")
        with open(output_path, 'w', encoding='utf-8') as f:
            for item in data:
                f.write(json.dumps(item, ensure_ascii=False) + '\n')
        
        print(f"저장 완료: {len(data):,}개 레코드")

    def split_and_save_sft_dataset(
        self,
        input_file: Optional[Path] = None,
        train_ratio: float = 0.8,
        val_ratio: float = 0.1,
        test_ratio: float = 0.1,
        random_seed: int = 42,
        output_prefix: Optional[str] = None,
    ) -> Tuple[Path, Path, Path]:
        """SFT JSONL 파일을 로드, 분할, 저장합니다.

        Args:
            input_file: 입력 SFT JSONL 파일 경로 (None이면 자동 찾기)
            train_ratio: 학습 데이터 비율
            val_ratio: 검증 데이터 비율
            test_ratio: 테스트 데이터 비율
            random_seed: 랜덤 시드
            output_prefix: 출력 파일명 prefix (None이면 입력 파일명 사용)

        Returns:
            (train_path, val_path, test_path) 튜플
        """
        # 데이터 로드
        data = self.load_sft_jsonl(input_file)

        # 분할
        train_data, val_data, test_data = self.split_dataset(
            data,
            train_ratio=train_ratio,
            val_ratio=val_ratio,
            test_ratio=test_ratio,
            random_seed=random_seed,
        )

        # 출력 파일명 결정
        if input_file is None:
            sft_files = list(self.data_dir.glob("*.sft.jsonl"))
            input_file = sft_files[0]

        if output_prefix is None:
            output_prefix = Path(input_file).stem.replace('.sft', '')

        # 파일 저장
        train_path = self.data_dir / f"{output_prefix}_train.jsonl"
        val_path = self.data_dir / f"{output_prefix}_val.jsonl"
        test_path = self.data_dir / f"{output_prefix}_test.jsonl"

        self.save_jsonl(train_data, train_path)
        self.save_jsonl(val_data, val_path)
        self.save_jsonl(test_data, test_path)

        print(f"\n{'='*60}")
        print("데이터셋 분할 및 저장 완료!")
        print(f"{'='*60}")
        print(f"Train: {train_path.name}")
        print(f"Val:   {val_path.name}")
        print(f"Test:  {test_path.name}")

        return train_path, val_path, test_path

    def get_dataset_statistics(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """데이터셋 통계를 계산합니다.

        Args:
            data: 데이터 리스트

        Returns:
            통계 딕셔너리
        """
        if not data:
            return {}

        # Action 분포 계산
        actions = {}
        for item in data:
            try:
                output = json.loads(item.get("output", "{}"))
                action = output.get("action", "UNKNOWN")
                actions[action] = actions.get(action, 0) + 1
            except:
                actions["PARSE_ERROR"] = actions.get("PARSE_ERROR", 0) + 1

        # 평균 confidence 계산
        confidences = []
        for item in data:
            try:
                output = json.loads(item.get("output", "{}"))
                conf = output.get("confidence", 0.0)
                if isinstance(conf, (int, float)):
                    confidences.append(conf)
            except:
                pass

        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

        return {
            "total_count": len(data),
            "action_distribution": actions,
            "average_confidence": avg_confidence,
        }


if __name__ == "__main__":
    """메인 실행 함수."""
    print("=" * 60)
    print("SFT 데이터셋 Train/Val/Test 분할")
    print("=" * 60)

    # Repository 생성
    repo = SpamDatasetRepository()

    # 데이터셋 분할 및 저장
    train_path, val_path, test_path = repo.split_and_save_sft_dataset(
        train_ratio=0.8,
        val_ratio=0.1,
        test_ratio=0.1,
        random_seed=42,
    )

    # 통계 출력
    print("\n" + "=" * 60)
    print("데이터셋 통계")
    print("=" * 60)

    train_data = repo.load_sft_jsonl(train_path)
    val_data = repo.load_sft_jsonl(val_path)
    test_data = repo.load_sft_jsonl(test_path)

    print("\n[Train 데이터셋]")
    train_stats = repo.get_dataset_statistics(train_data)
    print(f"  총 레코드: {train_stats.get('total_count', 0):,}개")
    print(f"  Action 분포: {train_stats.get('action_distribution', {})}")
    print(f"  평균 Confidence: {train_stats.get('average_confidence', 0.0):.2f}")

    print("\n[Val 데이터셋]")
    val_stats = repo.get_dataset_statistics(val_data)
    print(f"  총 레코드: {val_stats.get('total_count', 0):,}개")
    print(f"  Action 분포: {val_stats.get('action_distribution', {})}")
    print(f"  평균 Confidence: {val_stats.get('average_confidence', 0.0):.2f}")

    print("\n[Test 데이터셋]")
    test_stats = repo.get_dataset_statistics(test_data)
    print(f"  총 레코드: {test_stats.get('total_count', 0):,}개")
    print(f"  Action 분포: {test_stats.get('action_distribution', {})}")
    print(f"  평균 Confidence: {test_stats.get('average_confidence', 0.0):.2f}")

    print("\n" + "=" * 60)
    print("완료!")
    print("=" * 60)
