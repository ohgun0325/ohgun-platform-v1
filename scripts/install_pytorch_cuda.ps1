# PyTorch CUDA 버전 설치 스크립트 (PowerShell)

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "PyTorch CUDA 버전 설치 스크립트" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Python 버전 확인
Write-Host "[1] Python 버전 확인" -ForegroundColor Yellow
$pythonVersion = python --version 2>&1
Write-Host "  $pythonVersion" -ForegroundColor Gray

if ($pythonVersion -match "3\.13") {
    Write-Host ""
    Write-Host "[WARNING] Python 3.13은 PyTorch CUDA 빌드가 완전히 지원되지 않을 수 있습니다." -ForegroundColor Yellow
    Write-Host "  Python 3.11 또는 3.12 사용을 권장합니다." -ForegroundColor Yellow
    Write-Host ""
    $continue = Read-Host "계속 진행하시겠습니까? (y/n)"
    if ($continue -ne "y" -and $continue -ne "Y") {
        Write-Host "설치를 취소했습니다." -ForegroundColor Red
        exit
    }
}

Write-Host ""
Write-Host "[2] 기존 PyTorch 제거" -ForegroundColor Yellow
pip uninstall torch torchvision torchaudio -y

Write-Host ""
Write-Host "[3] PyTorch CUDA 버전 설치 시도" -ForegroundColor Yellow
Write-Host "  방법 1: CUDA 12.1 버전" -ForegroundColor Gray

# 방법 1: CUDA 12.1
Write-Host "  설치 중..." -ForegroundColor Gray
pip install torch torchvision torchaudio --extra-index-url https://download.pytorch.org/whl/cu121

Write-Host ""
Write-Host "[4] 설치 확인" -ForegroundColor Yellow
$env:KMP_DUPLICATE_LIB_OK = "TRUE"
$result = python -c "import torch; print('PyTorch:', torch.__version__); print('CUDA:', torch.cuda.is_available())" 2>&1

if ($LASTEXITCODE -eq 0) {
    Write-Host $result -ForegroundColor Gray
    Write-Host ""
    
    if ($result -match "CUDA: True") {
        Write-Host "============================================================" -ForegroundColor Green
        Write-Host "PyTorch CUDA 버전 설치 성공!" -ForegroundColor Green
        Write-Host "============================================================" -ForegroundColor Green
        Write-Host ""
        Write-Host "다음 단계:" -ForegroundColor Yellow
        Write-Host "  1. pip install -r requirements.txt" -ForegroundColor Gray
        Write-Host "  2. python scripts/check_cuda.py" -ForegroundColor Gray
    } else {
        Write-Host "============================================================" -ForegroundColor Red
        Write-Host "CUDA 버전이 설치되지 않았습니다." -ForegroundColor Red
        Write-Host "============================================================" -ForegroundColor Red
        Write-Host ""
        Write-Host "가능한 원인:" -ForegroundColor Yellow
        Write-Host "  1. Python 3.13에서 CUDA 빌드가 제공되지 않음" -ForegroundColor Gray
        Write-Host "  2. CUDA 버전 호환성 문제" -ForegroundColor Gray
        Write-Host ""
        Write-Host "해결 방법:" -ForegroundColor Yellow
        Write-Host "  1. Python 3.12로 다운그레이드 (권장)" -ForegroundColor Gray
        Write-Host "  2. docs/PYTORCH_CUDA_INSTALL.md 참고" -ForegroundColor Gray
    }
} else {
    Write-Host "============================================================" -ForegroundColor Red
    Write-Host "설치 확인 중 오류 발생" -ForegroundColor Red
    Write-Host "============================================================" -ForegroundColor Red
}
