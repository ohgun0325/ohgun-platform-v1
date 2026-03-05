# 스팸 에이전트 실행 스크립트 (환경 변수 자동 설정)

# OpenMP 라이브러리 중복 문제 해결
$env:KMP_DUPLICATE_LIB_OK = "TRUE"

# 실행할 스크립트 선택
param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("extract", "transform", "load_model", "all")]
    [string]$Action
)

$projectRoot = $PSScriptRoot

switch ($Action) {
    "extract" {
        Write-Host "Extract 단계 실행..." -ForegroundColor Cyan
        python "$projectRoot\app\service\spam_agent\extract_jsonl.py"
    }
    "transform" {
        Write-Host "Transform 단계 실행..." -ForegroundColor Cyan
        python "$projectRoot\app\service\spam_agent\transform_jsonl.py"
    }
    "load_model" {
        Write-Host "모델 로드 테스트..." -ForegroundColor Cyan
        python "$projectRoot\app\service\spam_agent\load_model.py"
    }
    "all" {
        Write-Host "전체 파이프라인 실행..." -ForegroundColor Cyan
        python "$projectRoot\app\service\spam_agent\extract_jsonl.py"
        python "$projectRoot\app\service\spam_agent\transform_jsonl.py"
        python "$projectRoot\app\service\spam_agent\load_model.py"
    }
}
