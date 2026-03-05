# KOICA 데이터로 Exaone 모델 훈련 실행 스크립트
# OpenMP 에러를 방지하기 위해 환경 변수를 설정하고 훈련을 실행합니다.

# 환경 변수 설정
$env:KMP_DUPLICATE_LIB_OK = "TRUE"

Write-Host ("=" * 60)
Write-Host "Exaone 모델 훈련 시작 (KOICA 데이터)"
Write-Host ("=" * 60)
Write-Host ""
Write-Host "[INFO] 환경 변수 설정: KMP_DUPLICATE_LIB_OK=TRUE" -ForegroundColor Green
Write-Host ""

# Python 스크립트 실행
python scripts/train_exaone_koica.py

# 종료 코드 전달
exit $LASTEXITCODE
