# OpenMP 라이브러리 중복 문제 해결을 위한 환경 변수 설정 스크립트

# 사용자 환경 변수에 영구적으로 추가
[System.Environment]::SetEnvironmentVariable("KMP_DUPLICATE_LIB_OK", "TRUE", "User")

Write-Host "환경 변수가 설정되었습니다: KMP_DUPLICATE_LIB_OK=TRUE" -ForegroundColor Green
Write-Host ""
Write-Host "주의: 새 터미널을 열어야 변경사항이 적용됩니다." -ForegroundColor Yellow
Write-Host ""
Write-Host "또는 현재 세션에서만 사용하려면:" -ForegroundColor Cyan
Write-Host '  $env:KMP_DUPLICATE_LIB_OK="TRUE"' -ForegroundColor White
