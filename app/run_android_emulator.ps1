# 한글 경로(예: OneDrive\문서)에서 Android 빌드 시 "Illegal byte sequence" 오류를 피하기 위해
# 가상 드라이브(subst)로 ASCII 경로를 만든 뒤 Flutter 앱을 에뮬레이터에서 실행합니다.
# 사용법: PowerShell에서 app.ohgun.kr 폴더로 이동 후 .\run_android_emulator.ps1

$ErrorActionPreference = "Stop"
$flutterDir = $PSScriptRoot
$projectRoot = (Get-Item $flutterDir).Parent.FullName
$driveLetter = "Z:"

# 이미 Z:가 다른 경로로 매핑되어 있으면 제거
$existing = (Get-PSDrive -Name Z -ErrorAction SilentlyContinue)
if ($existing) {
    subst ${driveLetter} /D 2>$null
}

Write-Host "Project root: $projectRoot"
Write-Host "Mapping ${driveLetter} to project root (ASCII path for Android build)..."
subst ${driveLetter} $projectRoot

try {
    Set-Location "${driveLetter}\app.ohgun.kr"
    Write-Host "Cleaning previous build..."
    flutter clean
    flutter pub get
    # 기기 ID 사용 (emulator-5554 등). 없으면 에뮬레이터가 목록에 있는지 확인 후 실행
    $devices = flutter devices 2>&1 | Out-String
    if ($devices -match "emulator-(\d+)") {
        $emuId = $Matches[0]
        Write-Host "Running on Android emulator (flutter run -d $emuId)..."
        flutter run -d $emuId
    } else {
        Write-Host "Running on first available device (flutter run)..."
        flutter run
    }
} finally {
    Set-Location $flutterDir
    Write-Host "Unmapping ${driveLetter}..."
    subst ${driveLetter} /D 2>$null
    Write-Host "Done."
}
