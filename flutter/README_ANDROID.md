# Android 에뮬레이터에서 실행하기

## 한글 경로 오류 (Illegal byte sequence)

프로젝트 경로에 **한글**(예: `OneDrive\문서`)이 있으면 Android 빌드 도구(aapt)가 APK 경로를 처리하지 못해 다음 오류가 납니다.

- `Unable to open ... Illegal byte sequence`
- `Error opening archive` / `AndroidManifest.xml not found`
- `No application found for TargetPlatform.android_x64`

### 해결 방법

**방법 1: 스크립트로 실행 (권장)**  
가상 드라이브(subst)로 ASCII 경로를 만들어 빌드하므로, 기존 폴더를 옮기지 않아도 됩니다.

```powershell
cd flutter
.\run_android_emulator.ps1
```

에뮬레이터가 켜져 있어야 합니다. Android Studio에서 AVD를 먼저 실행하거나, `flutter emulators` / `flutter emulators --launch <id>` 로 실행하세요.

**방법 2: 프로젝트를 영문 경로로 복사**  
예: `C:\projects\langchain` 처럼 경로에 한글이 없게 복사한 뒤, 그곳에서 `flutter run -d android` 를 실행합니다.

## 일반 실행 (경로에 한글이 없는 경우)

```powershell
cd flutter
flutter clean
flutter pub get
flutter run -d android
```
