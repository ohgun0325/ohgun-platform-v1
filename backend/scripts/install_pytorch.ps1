# PyTorch 설치 스크립트 (PowerShell)
# CUDA 12.1 버전 설치

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "PyTorch 설치 스크립트 (CUDA 12.1)" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# 방법 1: pip install with extra-index-url
Write-Host "[방법 1] pip install with extra-index-url 사용" -ForegroundColor Yellow
Write-Host "명령어: pip install torch torchvision torchaudio --extra-index-url https://download.pytorch.org/whl/cu121" -ForegroundColor Gray
Write-Host ""

# 방법 2: 환경 변수 설정 후 설치
Write-Host "[방법 2] 환경 변수 설정 후 설치" -ForegroundColor Yellow
Write-Host "명령어:" -ForegroundColor Gray
Write-Host "  `$env:PIP_EXTRA_INDEX_URL='https://download.pytorch.org/whl/cu121'" -ForegroundColor Gray
Write-Host "  pip install torch torchvision torchaudio" -ForegroundColor Gray
Write-Host ""

# 방법 3: 직접 URL 사용 (가장 안정적)
Write-Host "[방법 3] 직접 설치 (권장)" -ForegroundColor Green
Write-Host "명령어: pip install torch torchvision torchaudio -f https://download.pytorch.org/whl/torch_stable.html" -ForegroundColor Gray
Write-Host ""

# 방법 4: 공식 PyTorch 웹사이트 명령어
Write-Host "[방법 4] 공식 PyTorch 웹사이트 명령어" -ForegroundColor Yellow
Write-Host "https://pytorch.org/get-started/locally/ 에서 최신 명령어 확인" -ForegroundColor Gray
Write-Host ""

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "설치 시작..." -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# 방법 3 사용 (가장 안정적)
Write-Host "방법 3으로 설치 시도 중..." -ForegroundColor Yellow
pip install torch torchvision torchaudio -f https://download.pytorch.org/whl/torch_stable.html

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "============================================================" -ForegroundColor Green
    Write-Host "PyTorch 설치 완료!" -ForegroundColor Green
    Write-Host "============================================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "설치 확인을 위해 다음 명령어를 실행하세요:" -ForegroundColor Yellow
    Write-Host "  python scripts/check_cuda.py" -ForegroundColor Gray
} else {
    Write-Host ""
    Write-Host "============================================================" -ForegroundColor Red
    Write-Host "설치 실패. 다른 방법을 시도하세요." -ForegroundColor Red
    Write-Host "============================================================" -ForegroundColor Red
    Write-Host ""
    Write-Host "수동 설치 방법:" -ForegroundColor Yellow
    Write-Host "1. pip install torch torchvision torchaudio --extra-index-url https://download.pytorch.org/whl/cu121" -ForegroundColor Gray
    Write-Host "2. 또는 pip install torch torchvision torchaudio (CPU 버전)" -ForegroundColor Gray
}
