# 🚀 GitHub Actions CI/CD 배포 완벽 가이드

## ✅ 현재 설정 완료된 Secrets
- `EC2_HOST` ✓
- `EC2_SSH_KEY` ✓
- `EC2_USERNAME` ✓

## 📋 추가로 설정해야 할 Secrets

GitHub Repository → Settings → Secrets and variables → Actions → **New repository secret** 클릭

### 1. DATABASE_URL
```
이름: DATABASE_URL
값: postgresql://neondb_owner:npg_CgW5GmNnP0uq@ep-blue-bonus-a1zf9qhw-pooler.ap-southeast-1.aws.neon.tech:5432/neondb?sslmode=require
```

### 2. POSTGRES_PASSWORD
```
이름: POSTGRES_PASSWORD
값: npg_CgW5GmNnP0uq
```

### 3. GEMINI_API_KEY
```
이름: GEMINI_API_KEY
값: [여러분의 Gemini API 키]
```

---

## 🔄 CI/CD 배포 프로세스 (자동화 흐름)

### 전체 흐름도
```
┌─────────────────────────────────────────────────────────────┐
│  1. 개발자가 코드 작성 및 커밋                                │
│     git add .                                                │
│     git commit -m "feat: 새 기능 추가"                       │
│     git push origin main                                     │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  2. GitHub Actions 자동 트리거                               │
│     - main 브랜치 push 감지                                  │
│     - .github/workflows/deploy.yml 실행                      │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  3. Test Job (코드 검증)                                     │
│     ├─ 코드 체크아웃                                         │
│     ├─ Python 3.11 환경 설정                                 │
│     ├─ 종속성 설치 (requirements.txt)                        │
│     ├─ Flake8 린트 검사                                      │
│     └─ Config 로딩 테스트                                    │
│                                                              │
│     ❌ 실패시 → 배포 중단                                    │
│     ✅ 성공시 → Deploy Job으로 진행                          │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  4. Deploy Job (EC2 배포)                                    │
│                                                              │
│  Step 1: SSH 설정                                            │
│     - GitHub Secrets에서 EC2_SSH_KEY 가져오기                │
│     - ~/.ssh/id_rsa 파일 생성                                │
│     - 권한 설정 (chmod 600)                                  │
│     - known_hosts에 EC2 호스트 추가                          │
│                                                              │
│  Step 2: 환경 변수 파일 생성                                 │
│     - .env 파일 생성                                         │
│     - DATABASE_URL, GEMINI_API_KEY 등 주입                   │
│                                                              │
│  Step 3: 파일 동기화 (rsync)                                 │
│     - 로컬 파일 → EC2 서버로 전송                            │
│     - 제외: libs, node_modules, __pycache__                  │
│     - 경로: ~/langchain/                                     │
│                                                              │
│  Step 4: EC2에서 배포 실행                                   │
│     ├─ Docker 설치 확인 (없으면 자동 설치)                   │
│     ├─ Docker Compose 설치 확인                              │
│     ├─ 기존 컨테이너 중지 (docker-compose down)              │
│     ├─ 새 이미지 빌드 (docker-compose build)                 │
│     ├─ 컨테이너 시작 (docker-compose up -d)                  │
│     └─ 로그 출력 (최근 50줄)                                 │
│                                                              │
│  Step 5: 헬스체크                                            │
│     - 30초 대기                                              │
│     - http://EC2_HOST:8000/health 호출                       │
│     - 최대 10번 재시도 (10초 간격)                           │
│     - ✅ 성공 → 배포 완료                                    │
│     - ❌ 실패 → 배포 실패 알림                               │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  5. Notify Job (배포 결과 알림)                              │
│     - 배포 성공/실패 메시지 출력                             │
│     - GitHub Actions 로그에 기록                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 🎯 단계별 상세 설명

### **Step 1: 코드 Push (개발자)**

```bash
# 1. 코드 변경 후 커밋
git add .
git commit -m "feat: 새로운 API 엔드포인트 추가"

# 2. main 브랜치에 push
git push origin main
```

**이 순간 GitHub Actions가 자동으로 트리거됩니다!**

---

### **Step 2: GitHub Actions 실행**

GitHub Repository → **Actions** 탭에서 실행 상태 확인 가능

#### 실행 화면 예시:
```
✓ Test (1m 23s)
  ├─ Checkout code
  ├─ Set up Python
  ├─ Install dependencies
  ├─ Lint with flake8
  └─ Check config.py

⏳ Deploy (2m 45s)
  ├─ Checkout code
  ├─ Configure SSH
  ├─ Create .env file
  ├─ Copy files to EC2
  ├─ Deploy on EC2
  ├─ Health Check
  └─ Cleanup SSH

✓ Notify (5s)
  └─ Deployment Status
```

---

### **Step 3: Test Job 실행**

```yaml
# 1. Python 환경 설정
- Python 3.11 설치
- pip 업그레이드
- requirements.txt 설치

# 2. 코드 품질 검사
- flake8로 문법 에러 검사
- 복잡도 분석

# 3. 설정 파일 검증
- config.py 로딩 테스트
```

**✅ 모든 테스트 통과시 Deploy Job 실행**
**❌ 하나라도 실패시 배포 중단**

---

### **Step 4: Deploy Job 실행 (핵심)**

#### 4-1. SSH 연결 설정
```bash
# GitHub Secrets에서 SSH 키 가져오기
mkdir -p ~/.ssh
echo "$EC2_SSH_KEY" > ~/.ssh/id_rsa
chmod 600 ~/.ssh/id_rsa

# EC2 호스트 신뢰 목록에 추가
ssh-keyscan -H $EC2_HOST >> ~/.ssh/known_hosts
```

#### 4-2. 환경 변수 파일 생성
```bash
# .env 파일 생성 (GitHub Secrets 값 주입)
cat > .env << EOF
DATABASE_URL=${{ secrets.DATABASE_URL }}
POSTGRES_PASSWORD=${{ secrets.POSTGRES_PASSWORD }}
GEMINI_API_KEY=${{ secrets.GEMINI_API_KEY }}
USE_QLORA=true
QLORA_MODEL_NAME=K-intelligence/Midm-2.0-Mini-Instruct
CORS_ORIGINS=*
EOF
```

#### 4-3. 파일 동기화 (rsync)
```bash
# EC2에 디렉토리 생성
ssh ubuntu@EC2_HOST "mkdir -p ~/langchain"

# 파일 전송 (불필요한 파일 제외)
rsync -avz \
  --exclude 'libs' \
  --exclude 'frontend/node_modules' \
  --exclude '__pycache__' \
  --exclude '*.pyc' \
  ./ ubuntu@EC2_HOST:~/langchain/
```

**전송되는 파일들:**
- `app/` (FastAPI 애플리케이션)
- `Dockerfile`
- `docker-compose.yml`
- `requirements.txt`
- `config.py`
- `.env` (방금 생성한 환경 변수)
- 기타 필요한 파일들

#### 4-4. EC2에서 Docker 배포
```bash
# EC2에 SSH 접속하여 명령 실행
ssh ubuntu@EC2_HOST << 'EOF'
  cd ~/langchain

  # Docker 설치 확인 (없으면 자동 설치)
  if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
  fi

  # Docker Compose 설치 확인
  if ! command -v docker-compose &> /dev/null; then
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
  fi

  # 기존 컨테이너 중지
  docker-compose down

  # 새 이미지 빌드 및 컨테이너 시작
  docker-compose up -d --build

  # 상태 확인
  docker-compose ps
  docker-compose logs --tail=50
EOF
```

**Docker가 하는 일:**
1. `Dockerfile` 읽기
2. Python 3.11 베이스 이미지 다운로드
3. 시스템 종속성 설치 (PostgreSQL 클라이언트 등)
4. `requirements.txt` 설치
5. 애플리케이션 코드 복사
6. 포트 8000 노출
7. FastAPI 서버 실행 (`uvicorn app.api_server:app`)

#### 4-5. 헬스체크
```bash
# 30초 대기 (서버 시작 시간)
sleep 30

# API 엔드포인트 확인 (최대 10번 시도)
for i in {1..10}; do
  if curl -f http://$EC2_HOST:8000/health; then
    echo "✅ Service is healthy!"
    exit 0
  fi
  echo "Attempt $i failed, retrying in 10s..."
  sleep 10
done
```

---

### **Step 5: Notify Job**

```bash
# 배포 결과 확인
if [ "deploy.result" == "success" ]; then
  echo "✅ Deployment successful to $EC2_HOST"
else
  echo "❌ Deployment failed"
fi
```

---

## 🎬 실제 배포 시작하기

### 방법 1: 코드 변경 후 자동 배포 (권장)

```bash
# 1. 추가 Secrets 설정 (위 참조)
# 2. 코드 변경
echo "# Test deployment" >> README.md

# 3. Git 커밋 및 푸시
git add .
git commit -m "test: CI/CD 배포 테스트"
git push origin main

# 4. GitHub Actions 확인
# https://github.com/your-username/your-repo/actions
```

### 방법 2: 수동 트리거

1. GitHub Repository → **Actions** 탭
2. **CI/CD Pipeline - Deploy to EC2** 선택
3. **Run workflow** 버튼 클릭
4. 브랜치 선택 (main)
5. **Run workflow** 실행

---

## 📊 배포 진행 상황 확인

### GitHub Actions 로그 확인

```
GitHub Repository → Actions → 최신 워크플로우 클릭

각 단계별 로그 확인:
✓ Test
  └─ 각 step 클릭하여 상세 로그 확인

⏳ Deploy
  └─ "Deploy on EC2" step에서 Docker 로그 확인

✓ Notify
  └─ 최종 배포 결과 확인
```

### EC2에서 직접 확인

```bash
# 1. EC2 SSH 접속
ssh -i "your-key.pem" ubuntu@your-ec2-ip

# 2. 컨테이너 상태 확인
cd ~/langchain
docker-compose ps

# 출력 예시:
# NAME                COMMAND                  STATUS    PORTS
# langchain-fastapi   "uvicorn app.api_ser…"   Up        0.0.0.0:8000->8000/tcp

# 3. 로그 실시간 확인
docker-compose logs -f fastapi

# 4. API 테스트
curl http://localhost:8000/health
```

---

## 🌐 배포 완료 후 API 테스트

### 1. 헬스체크
```bash
curl http://your-ec2-ip:8000/health

# 응답 예시:
{
  "status": "healthy",
  "database": "connected",
  "embedding_dimension": 768,
  "gemini_available": true,
  "model_type": "QLoRA"
}
```

### 2. API 문서 확인
브라우저에서 접속:
```
http://your-ec2-ip:8000/docs
```

Swagger UI가 표시되며 모든 API 엔드포인트 확인 가능

### 3. 채팅 API 테스트
```bash
curl -X POST "http://your-ec2-ip:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "안녕하세요, LangChain에 대해 알려주세요"
  }'

# 응답 예시:
{
  "response": "LangChain은 대규모 언어 모델을 활용한...",
  "sources": [
    "Document 1: ...",
    "Document 2: ..."
  ]
}
```

### 4. 검색 API 테스트
```bash
curl -X POST "http://your-ec2-ip:8000/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "LangChain",
    "limit": 3
  }'
```

---

## 🔄 재배포 (코드 업데이트시)

```bash
# 1. 코드 수정
vim app/api_server.py

# 2. 커밋 및 푸시
git add .
git commit -m "fix: API 응답 형식 수정"
git push origin main

# 3. GitHub Actions 자동 실행
# - 기존 컨테이너 중지
# - 새 코드로 이미지 재빌드
# - 새 컨테이너 시작
# - 헬스체크

# 4. 무중단 배포 완료!
```

**배포 시간: 약 3-5분**

---

## 🐛 트러블슈팅

### 문제 1: GitHub Actions에서 SSH 연결 실패

**증상:**
```
Permission denied (publickey)
```

**해결:**
1. `EC2_SSH_KEY` Secret 확인
2. SSH 키 전체 내용 포함 확인 (`-----BEGIN` ~ `-----END`)
3. EC2 보안 그룹에서 포트 22 오픈 확인

### 문제 2: Health Check 실패

**증상:**
```
❌ Health check failed
```

**해결:**
```bash
# EC2에 접속하여 로그 확인
ssh ubuntu@your-ec2-ip
cd ~/langchain
docker-compose logs -f

# 일반적인 원인:
# - 환경 변수 누락 (DATABASE_URL, GEMINI_API_KEY)
# - 포트 8000이 이미 사용 중
# - 메모리 부족 (QLoRA 모델 로딩시)
```

### 문제 3: Docker 빌드 실패

**증상:**
```
ERROR: failed to solve: process "/bin/sh -c pip install -r requirements.txt" did not complete successfully
```

**해결:**
```bash
# requirements.txt 확인
# 특정 패키지 버전 문제일 수 있음

# EC2에서 수동 빌드 테스트
cd ~/langchain
docker-compose build --no-cache
```

### 문제 4: 포트 8000 접근 불가

**해결:**
1. EC2 보안 그룹 확인
   - Inbound Rules에 포트 8000 추가
   - 소스: `0.0.0.0/0` (또는 특정 IP)

2. 방화벽 확인
```bash
sudo ufw status
sudo ufw allow 8000
```

---

## 📈 배포 성공 확인 체크리스트

- [ ] GitHub Secrets 6개 모두 설정 완료
- [ ] GitHub Actions 워크플로우 실행 성공
- [ ] Test Job 통과
- [ ] Deploy Job 통과
- [ ] Health Check 통과
- [ ] `http://EC2_IP:8000/health` 응답 확인
- [ ] `http://EC2_IP:8000/docs` API 문서 접속 가능
- [ ] 채팅 API 테스트 성공
- [ ] EC2에서 `docker-compose ps` 컨테이너 실행 중

---

## 🎉 축하합니다!

CI/CD 파이프라인이 성공적으로 구축되었습니다!

이제부터는:
- `git push origin main` 만 하면 자동으로 배포됩니다
- 코드 품질 검사가 자동으로 실행됩니다
- 배포 실패시 자동으로 알림을 받습니다
- 무중단 배포가 가능합니다

**다음 단계:**
1. 도메인 연결 (Route 53)
2. HTTPS 설정 (Let's Encrypt)
3. 모니터링 설정 (CloudWatch)
4. 로드 밸런서 추가 (ALB)

