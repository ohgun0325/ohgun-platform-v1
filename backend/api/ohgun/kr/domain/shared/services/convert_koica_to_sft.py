"""KOICA JSONL 파일을 SFT 형식으로 변환하는 모듈.

기존 convert_koica_to_jsonl.py에서 생성한 JSONL 파일을 읽어서
더 구조화된 SFT 형식으로 변환합니다.
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


def iter_jsonl(path: Path) -> Iterable[Dict[str, Any]]:
    """JSONL을 한 줄씩 읽습니다. 깨진 라인은 건너뜁니다.

    Args:
        path: 읽을 JSONL 파일 경로

    Yields:
        각 행의 JSON 객체 딕셔너리
    """
    with path.open("r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                print(f"경고: {path.name}의 {lineno}번째 줄을 파싱할 수 없습니다. 건너뜁니다.")
                continue


def write_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    """JSONL 파일로 저장합니다.

    Args:
        path: 저장할 파일 경로
        rows: 저장할 딕셔너리들의 반복 가능 객체
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def normalize_koica_data(row: Dict[str, Any]) -> Dict[str, Any]:
    """KOICA JSONL 형식의 row를 정규화합니다.

    Args:
        row: 기존 JSONL 행 데이터 (instruction, input, output 포함)

    Returns:
        정규화된 딕셔너리
    """
    return {
        "instruction": row.get("instruction", "").strip(),
        "input": row.get("input", "").strip(),
        "output": row.get("output", "").strip(),
    }


def dedup_key(clean: Dict[str, Any]) -> Tuple:
    """중복 제거 기준을 반환합니다.

    Args:
        clean: 정규화된 데이터 딕셔너리

    Returns:
        중복 체크용 튜플 키
    """
    # instruction + input 조합으로 중복 체크
    return (
        clean.get("instruction", ""),
        clean.get("input", ""),
    )


def to_sft(clean: Dict[str, Any]) -> Dict[str, Any]:
    """정규화된 데이터를 SFT 형식으로 변환합니다.

    Args:
        clean: 정규화된 데이터 딕셔너리

    Returns:
        SFT 형식의 딕셔너리
    """
    # 이미 instruction-input-output 형식이므로 그대로 반환
    return {
        "instruction": clean.get("instruction", ""),
        "input": clean.get("input", ""),
        "output": clean.get("output", ""),
    }


def convert_jsonl_to_sft(
    input_jsonl_path: Path,
    output_sft_path: Path,
    output_dedup_path: Optional[Path] = None,
) -> Tuple[int, int]:
    """JSONL 파일을 SFT 형식으로 변환합니다.

    Args:
        input_jsonl_path: 입력 JSONL 파일 경로
        output_sft_path: 출력 SFT JSONL 파일 경로
        output_dedup_path: (선택) 중복 제거된 JSONL 파일 경로

    Returns:
        (sft_count, dedup_count) 튜플
    """
    seen = set()
    dedup_rows = []
    sft_rows = []
    
    total_count = 0
    for row in iter_jsonl(input_jsonl_path):
        total_count += 1
        if total_count % 1000 == 0:
            print(f"처리 중: {total_count}개 레코드...")
        
        clean = normalize_koica_data(row)
        key = dedup_key(clean)
        
        if key in seen:
            continue
        seen.add(key)
        
        # dedup 단계 산출물
        if output_dedup_path is not None:
            dedup_rows.append(row)
        
        # sft 산출물
        sft_rows.append(to_sft(clean))
    
    # 저장
    print(f"SFT 파일 저장 중: {output_sft_path}")
    write_jsonl(output_sft_path, sft_rows)
    
    if output_dedup_path is not None:
        print(f"중복 제거 파일 저장 중: {output_dedup_path}")
        write_jsonl(output_dedup_path, dedup_rows)
    
    return len(sft_rows), len(dedup_rows)


def main():
    """메인 함수: koica_data 폴더의 모든 JSONL 파일을 SFT 형식으로 변환합니다."""
    project_root = Path(__file__).parent.parent.parent
    koica_data_dir = project_root / "data" / "koica_data"
    
    if not koica_data_dir.exists():
        print(f"[ERROR] 디렉토리를 찾을 수 없습니다: {koica_data_dir}")
        sys.exit(1)
    
    # JSONL 파일 찾기 (.sft.jsonl 파일은 제외)
    jsonl_files = [f for f in koica_data_dir.glob("*.jsonl") 
                   if not f.name.endswith(".sft.jsonl")]
    
    if not jsonl_files:
        print(f"[WARNING] '{koica_data_dir}' 디렉토리에서 JSONL 파일을 찾을 수 없습니다.")
        print("먼저 convert_koica_to_jsonl.py를 실행하여 JSONL 파일을 생성하세요.")
        sys.exit(1)
    
    print(f"총 {len(jsonl_files)}개의 JSONL 파일을 찾았습니다.\n")
    
    total_sft = 0
    for jsonl_file in jsonl_files:
        print(f"{'='*60}")
        print(f"변환 중: {jsonl_file.name} -> {jsonl_file.stem}.sft.jsonl")
        print(f"{'='*60}")
        
        try:
            sft_file = jsonl_file.with_suffix(".sft.jsonl")
            sft_count, dedup_count = convert_jsonl_to_sft(
                input_jsonl_path=jsonl_file,
                output_sft_path=sft_file,
            )
            total_sft += sft_count
            print(f"\n[OK] SFT 변환 완료:")
            print(f"  - SFT 레코드: {sft_count:,}개")
            print(f"  - 중복 제거: {len(list(iter_jsonl(jsonl_file))) - sft_count:,}개")
            print(f"  - 출력 파일: {sft_file.name}\n")
        except Exception as e:
            print(f"[ERROR] {jsonl_file.name} 변환 실패: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    print("\n" + "=" * 60)
    print(f"모든 변환 작업이 완료되었습니다. (총 {total_sft:,}개 SFT 레코드)")
    print("=" * 60)


if __name__ == "__main__":
    main()
