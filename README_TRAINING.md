# Exaone 모델 훈련 가이드

## OpenMP 에러 해결

Windows에서 PyTorch를 사용할 때 OpenMP 라이브러리 중복 에러가 발생할 수 있습니다. 
이 문제를 해결하기 위해 환경 변수 `KMP_DUPLICATE_LIB_OK=TRUE`를 설정해야 합니다.

### 해결 방법

#### 방법 1: PowerShell 스크립트 사용 (권장)

```powershell
# 훈련 실행 스크립트 사용
.\scripts\run_train_koica.ps1
```

또는

```powershell
# 환경 변수만 설정
.\scripts\set_env.ps1
python scripts/train_exaone_koica.py
```

#### 방법 2: PowerShell에서 직접 환경 변수 설정

```powershell
$env:KMP_DUPLICATE_LIB_OK = "TRUE"
python scripts/train_exaone_koica.py
```

#### 방법 3: Python 스크립트 자체에 포함됨 (자동 해결)

모든 훈련 스크립트는 자동으로 환경 변수를 설정하므로, 
다음 명령어로 바로 실행할 수 있습니다:

```powershell
python scripts/train_exaone_koica.py
```

### 영구적으로 환경 변수 설정 (선택사항)

PowerShell 프로필에 추가하여 매번 설정할 필요 없이 사용할 수 있습니다:

```powershell
# 프로필 편집
notepad $PROFILE

# 다음 줄 추가
$env:KMP_DUPLICATE_LIB_OK = "TRUE"
```

## 훈련 실행

### 1. 환경 확인

```powershell
python scripts/check_training_setup.py
```

또는

```powershell
python scripts/test_gpu_qlora.py
```

### 2. 데이터 준비 (이미 완료됨)

```powershell
python scripts/prepare_koica_data.py
```

### 3. 훈련 실행

```powershell
# 방법 1: PowerShell 스크립트 사용
.\scripts\run_train_koica.ps1

# 방법 2: 직접 실행
python scripts/train_exaone_koica.py
```

## 훈련 설정

- **모델**: Exaone-2.4b
- **방법**: QLoRA (4-bit 양자화)
- **에포크**: 3
- **배치 크기**: 4
- **학습률**: 2e-4
- **최대 시퀀스 길이**: 512

## 출력

훈련된 모델은 `models/exaone-koica-classifier/` 폴더에 저장됩니다:
- `adapter_model.safetensors`: LoRA 어댑터 가중치
- `adapter_config.json`: LoRA 설정
- `tokenizer files`: 토크나이저 파일들
