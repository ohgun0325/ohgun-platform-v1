"""HuggingFace에서 KoElectra 모델 다운로드 스크립트

사용법:
    python scripts/download_koelectra_model.py
"""

import os
from pathlib import Path

# OpenMP 라이브러리 중복 문제 해결
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

try:
    from huggingface_hub import snapshot_download
except ImportError:
    raise ImportError(
        "huggingface_hub 패키지가 필요합니다.\n"
        "설치: pip install huggingface_hub"
    )


def download_koelectra_model():
    """monologg/koelectra-small-v3-discriminator 모델을 다운로드합니다."""
    # 프로젝트 루트 경로
    project_root = Path(__file__).parent.parent
    models_dir = project_root / "models"
    models_dir.mkdir(exist_ok=True)
    
    model_name = "monologg/koelectra-small-v3-discriminator"
    output_dir = models_dir / "koelectra-small-v3-discriminator"
    
    print("=" * 60)
    print("KoElectra 모델 다운로드 시작")
    print("=" * 60)
    print(f"모델: {model_name}")
    print(f"저장 경로: {output_dir}")
    print()
    
    # 이미 다운로드되어 있는지 확인
    if output_dir.exists() and any(output_dir.iterdir()):
        print(f"[WARNING] 모델이 이미 존재합니다: {output_dir}")
        response = input("다시 다운로드하시겠습니까? (y/N): ")
        if response.lower() != 'y':
            print("다운로드를 취소했습니다.")
            return
        print("기존 모델을 덮어씁니다...")
    
    try:
        print("다운로드 중... (시간이 걸릴 수 있습니다)")
        snapshot_download(
            repo_id=model_name,
            local_dir=str(output_dir),
            local_dir_use_symlinks=False,  # 심볼릭 링크 대신 실제 파일 복사
        )
        
        print()
        print("=" * 60)
        print("[OK] 모델 다운로드 완료!")
        print("=" * 60)
        print(f"저장 위치: {output_dir}")
        
        # 다운로드된 파일 확인
        files = list(output_dir.rglob("*"))
        print(f"\n다운로드된 파일 수: {len(files)}")
        print("\n주요 파일:")
        for file in sorted(files)[:10]:  # 처음 10개만 표시
            if file.is_file():
                size_mb = file.stat().st_size / (1024 * 1024)
                print(f"  - {file.name}: {size_mb:.2f} MB")
        
    except Exception as e:
        print()
        print("=" * 60)
        print("[ERROR] 다운로드 실패!")
        print("=" * 60)
        print(f"오류: {e}")
        raise


if __name__ == "__main__":
    download_koelectra_model()
