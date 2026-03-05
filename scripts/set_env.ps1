# OpenMP 라이브러리 중복 문제 해결을 위한 환경 변수 설정
# PowerShell에서 이 스크립트를 실행하면 현재 세션에 환경 변수가 설정됩니다.

$env:KMP_DUPLICATE_LIB_OK = "TRUE"

Write-Host "[OK] 환경 변수 설정 완료: KMP_DUPLICATE_LIB_OK=TRUE" -ForegroundColor Green
Write-Host ""
Write-Host "이제 Python 스크립트를 실행할 수 있습니다:" -ForegroundColor Yellow
Write-Host "  python scripts/train_exaone_koica.py" -ForegroundColor Cyan
Write-Host ""
