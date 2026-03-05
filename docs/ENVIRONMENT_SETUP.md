# 환경 변수 설정 가이드

## OpenMP 라이브러리 중복 문제 해결

### 문제
```
OMP: Error #15: Initializing libiomp5md.dll, but found libiomp5md.dll already initialized.
```

### 해결 방법 (3가지 옵션)

---

## 방법 1: 코드 내 자동 설정 (권장) ✅

**이미 적용됨**: `load_model.py` 파일에 자동으로 설정되어 있습니다.

```python
# app/service/spam_agent/load_model.py 상단에 자동 추가됨
import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
```

**장점**:
- ✅ 별도 설정 불필요
- ✅ 다른 사람이 실행해도 문제없음
- ✅ 가장 편리함

**사용 방법**:
```bash
# 그냥 실행하면 됨!
python app/service/spam_agent/load_model.py
```

---

## 방법 2: 영구 환경 변수 설정

### Windows PowerShell

```powershell
# 사용자 환경 변수에 영구적으로 추가
[System.Environment]::SetEnvironmentVariable("KMP_DUPLICATE_LIB_OK", "TRUE", "User")
```

**또는 스크립트 실행:**
```powershell
.\setup_env.ps1
```

**주의**: 새 터미널을 열어야 적용됩니다.

### Windows CMD

```cmd
setx KMP_DUPLICATE_LIB_OK "TRUE"
```

**주의**: 새 터미널을 열어야 적용됩니다.

---

## 방법 3: 실행 스크립트 사용

### PowerShell 스크립트 사용

```powershell
# Extract 단계만
.\run_spam_agent.ps1 extract

# Transform 단계만
.\run_spam_agent.ps1 transform

# 모델 로드만
.\run_spam_agent.ps1 load_model

# 전체 파이프라인
.\run_spam_agent.ps1 all
```

**장점**:
- ✅ 환경 변수 자동 설정
- ✅ 명령어 간단
- ✅ 여러 단계 한 번에 실행 가능

---

## 현재 상태

### ✅ 이미 적용된 방법

**`app/service/spam_agent/load_model.py`** 파일에 자동 설정이 추가되었습니다:

```python
import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
```

따라서 **더 이상 수동으로 환경 변수를 설정할 필요가 없습니다!**

### 실행 방법

```bash
# 그냥 실행하면 됨
python app/service/spam_agent/load_model.py
```

---

## 다른 파일에도 적용하려면

만약 다른 Python 스크립트에서도 같은 문제가 발생한다면, 파일 상단에 추가하세요:

```python
import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

# 나머지 코드...
```

---

## 확인 방법

환경 변수가 설정되었는지 확인:

```powershell
# PowerShell
echo $env:KMP_DUPLICATE_LIB_OK

# CMD
echo %KMP_DUPLICATE_LIB_OK%
```

**출력**: `TRUE` (설정됨) 또는 빈 값 (설정 안 됨)

---

## 권장 사항

### ✅ 권장: 방법 1 (코드 내 자동 설정)

- 가장 편리함
- 다른 환경에서도 동작
- 설정 누락 방지

### ⚠️ 선택: 방법 2 (영구 환경 변수)

- 시스템 전체에 적용
- 다른 프로젝트에도 영향
- 새 터미널 필요

### 📝 편의: 방법 3 (실행 스크립트)

- 여러 명령어를 한 번에 실행
- 환경 변수 자동 설정
- 배치 작업에 유용

---

**작성일**: 2026-01-13  
**버전**: 1.0
