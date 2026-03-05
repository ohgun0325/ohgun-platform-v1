# 🚀 EC2 배포 가이드 - GitHub Actions CI/CD

이 문서는 FastAPI LangChain 애플리케이션을 AWS EC2에 GitHub Actions를 통해 자동으로 배포하는 방법을 설명합니다.

## 📋 목차

1. [배포 아키텍처](#배포-아키텍처)
2. [사전 준비사항](#사전-준비사항)
3. [EC2 인스턴스 설정](#ec2-인스턴스-설정)
4. [GitHub 설정](#github-설정)
5. [배포 프로세스](#배포-프로세스)
6. [트러블슈팅](#트러블슈팅)

---

## 배포 아키텍처

```
┌─────────────────┐      ┌──────────────────┐      ┌─────────────────┐
│  GitHub Repo    │─────▶│ GitHub Actions   │─────▶│   EC2 Instance  │
│  (main branch)  │      │  CI/CD Pipeline  │      │  Docker + App   │
└─────────────────┘      └──────────────────┘      └─────────────────┘
                                                              │
                                                              ▼
                                                    ┌─────────────────┐
                                                    │ Neon PostgreSQL │
                                                    │   (pgvector)    │
                                                    └─────────────────┘
```

### 배포 방식
- **Docker 기반**: 일관된 환경, 쉬운 롤백, 확장성
- **자동화**: `main` 브랜치 push 시 자동 배포
- **무중단 배포**: Docker Compose를 통한 컨테이너 교체

---

## 사전 준비사항

### 1. AWS EC2 인스턴스
- **권장 스펙**:
  - 타입: `t3.medium` 이상 (QLoRA 모델 사용시 `t3.large` 권장)
  - OS: Ubuntu 22.04 LTS
  - 스토리지: 20GB 이상
  - RAM: 4GB 이상 (QLoRA: 8GB 이상 권장)

### 2. 필요한 소프트웨어
- Docker & Docker Compose (자동 설치됨)
- SSH 접근 가능한 키페어

### 3. 네트워크 설정
- 보안 그룹에서 다음 포트 오픈:
  - `22` (SSH)
  - `8000` (FastAPI)
  - `80`, `443` (Nginx 사용시)

---

## EC2 인스턴스 설정

### 1. EC2 인스턴스 생성

```bash
# AWS Console에서 EC2 인스턴스 생성
# 1. Ubuntu 22.04 LTS AMI 선택
# 2. t3.medium 이상 선택
# 3. 키페어 생성 및 다운로드 (예: langchain-key.pem)
# 4. 보안 그룹 설정 (포트 22, 8000 오픈)
```

### 2. 초기 설정 (SSH 접속 후)

```bash
# SSH 접속
ssh -i "langchain-key.pem" ubuntu@your-ec2-public-ip

# 시스템 업데이트
sudo apt update && sudo apt upgrade -y

# 기본 유틸리티 설치
sudo apt install -y curl git

# Docker 설치 (GitHub Actions가 자동으로 설치하지만, 수동 배포시 필요)
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
newgrp docker

# Docker Compose 설치
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 설치 확인
docker --version
docker-compose --version
```

### 3. 디렉토리 구조 생성

```bash
mkdir -p ~/langchain/models/qlora_checkpoints
mkdir -p ~/langchain/static
cd ~/langchain
```

---

## GitHub 설정

### 1. Repository Secrets 설정

GitHub Repository → Settings → Secrets and variables → Actions → New repository secret

다음 시크릿들을 추가하세요:

| Secret Name | 설명 | 예시 |
|------------|------|------|
| `EC2_HOST` | EC2 퍼블릭 IP 또는 도메인 | `3.35.123.456` |
| `EC2_USERNAME` | EC2 사용자명 | `ubuntu` |
| `EC2_SSH_KEY` | SSH private key 전체 내용 | `-----BEGIN RSA PRIVATE KEY-----\n...` |
| `DATABASE_URL` | Neon PostgreSQL URL | `postgresql://user:pass@host:5432/db?sslmode=require` |
| `POSTGRES_PASSWORD` | PostgreSQL 비밀번호 | `your_password` |
| `GEMINI_API_KEY` | Google Gemini API 키 | `AIza...` |

#### EC2_SSH_KEY 설정 방법

```bash
# 로컬에서 SSH 키 내용 복사
cat langchain-key.pem

# 전체 내용을 복사하여 GitHub Secret에 추가
# -----BEGIN RSA PRIVATE KEY----- 부터
# -----END RSA PRIVATE KEY----- 까지 모두 포함
```

### 2. 워크플로우 활성화

- `.github/workflows/deploy.yml` 파일이 리포지토리에 있으면 자동으로 활성화됩니다.
- Actions 탭에서 워크플로우 실행 확인 가능

---

## 배포 프로세스

### 자동 배포 (GitHub Actions)

1. **코드 변경 후 Push**
```bash
git add .
git commit -m "feat: 새로운 기능 추가"
git push origin main
```

2. **GitHub Actions 자동 실행**
   - Test Job: 코드 품질 검사 및 테스트
   - Deploy Job: EC2에 배포
   - Notify Job: 배포 결과 알림

3. **배포 완료 확인**
```bash
# 브라우저에서 확인
http://your-ec2-host:8000/docs
http://your-ec2-host:8000/health
```

### 수동 배포 (deploy.sh 사용)

```bash
# 환경 변수 설정
export EC2_HOST="your-ec2-public-ip"
export EC2_USER="ubuntu"
export SSH_KEY="~/.ssh/langchain-key.pem"

# 실행 권한 부여
chmod +x deploy.sh

# 배포 실행
./deploy.sh
```

---

## 배포 후 확인사항

### 1. 서비스 상태 확인

```bash
# EC2에 SSH 접속
ssh -i "langchain-key.pem" ubuntu@your-ec2-host

# 컨테이너 상태 확인
cd ~/langchain
docker-compose ps

# 로그 확인
docker-compose logs -f fastapi
```

### 2. API 엔드포인트 테스트

```bash
# 헬스체크
curl http://your-ec2-host:8000/health

# API 문서
# 브라우저에서 http://your-ec2-host:8000/docs 접속

# 채팅 테스트
curl -X POST "http://your-ec2-host:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "안녕하세요"}'
```

### 3. 리소스 모니터링

```bash
# CPU/메모리 사용량
docker stats

# 디스크 사용량
df -h

# 시스템 리소스
htop  # sudo apt install htop
```

---

## 고급 설정

### 1. Nginx 리버스 프록시 설정 (HTTPS)

```bash
# docker-compose.yml의 nginx 섹션 주석 해제
# nginx.conf에서 도메인 설정

# Let's Encrypt SSL 인증서 발급
sudo apt install certbot
sudo certbot certonly --standalone -d your-domain.com
```

### 2. 환경별 배포 (develop, staging, production)

```yaml
# .github/workflows/deploy.yml 수정
on:
  push:
    branches:
      - main        # production
      - develop     # development
```

### 3. 롤백 전략

```bash
# EC2에서 이전 이미지로 롤백
docker-compose down
docker images  # 이전 이미지 ID 확인
docker tag <old-image-id> langchain-fastapi:latest
docker-compose up -d
```

---

## 트러블슈팅

### 문제 1: SSH 연결 실패

**증상**: GitHub Actions에서 "Permission denied (publickey)" 오류

**해결방법**:
```bash
# SSH 키 권한 확인
chmod 600 langchain-key.pem

# GitHub Secret의 EC2_SSH_KEY가 올바른지 확인
# - 전체 키 내용 포함 (BEGIN ~ END)
# - 줄바꿈이 \n으로 표현되는지 확인
```

### 문제 2: Docker 빌드 실패

**증상**: "Cannot connect to the Docker daemon"

**해결방법**:
```bash
# EC2에서 Docker 서비스 시작
sudo systemctl start docker
sudo systemctl enable docker

# 사용자를 docker 그룹에 추가
sudo usermod -aG docker $USER
newgrp docker
```

### 문제 3: 메모리 부족

**증상**: QLoRA 모델 로딩 중 OOM (Out of Memory) 에러

**해결방법**:
```bash
# QLoRA 비활성화
# .env 파일에서
USE_QLORA=false

# 또는 인스턴스 타입 업그레이드
# t3.medium → t3.large (8GB RAM)
```

### 문제 4: 포트 접근 불가

**증상**: 외부에서 API 접근 불가

**해결방법**:
```bash
# 보안 그룹 확인
# - Inbound Rules에 포트 8000 추가
# - 소스: 0.0.0.0/0 (또는 특정 IP)

# 방화벽 확인
sudo ufw status
sudo ufw allow 8000
```

### 문제 5: 데이터베이스 연결 실패

**증상**: "could not connect to server"

**해결방법**:
```bash
# 환경 변수 확인
docker-compose exec fastapi env | grep DATABASE

# Neon PostgreSQL 연결 테스트
psql "postgresql://user:pass@host:5432/db?sslmode=require"

# .env 파일 권한 확인
ls -la .env
```

---

## 로그 확인 및 디버깅

```bash
# 실시간 로그 확인
docker-compose logs -f

# 특정 컨테이너 로그만 확인
docker-compose logs -f fastapi

# 최근 100줄 확인
docker-compose logs --tail=100

# 컨테이너 내부 접속
docker-compose exec fastapi bash

# 컨테이너 재시작
docker-compose restart fastapi
```

---

## 성능 최적화

### 1. Gunicorn + Uvicorn Workers

`Dockerfile` 수정:
```dockerfile
CMD ["gunicorn", "app.api_server:app", "--workers", "4", "--worker-class", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000"]
```

### 2. Redis 캐싱 추가

`docker-compose.yml`에 Redis 추가:
```yaml
redis:
  image: redis:alpine
  ports:
    - "6379:6379"
```

### 3. 로그 로테이션

```bash
# Docker 로그 크기 제한
# /etc/docker/daemon.json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
```

---

## 보안 강화

### 1. SSH 키 기반 인증만 허용

```bash
sudo vi /etc/ssh/sshd_config
# PasswordAuthentication no
sudo systemctl restart sshd
```

### 2. 방화벽 설정

```bash
sudo ufw enable
sudo ufw allow 22/tcp
sudo ufw allow 8000/tcp
sudo ufw status
```

### 3. 환경 변수 암호화

GitHub Actions에서 Secret 사용:
```yaml
env:
  DATABASE_URL: ${{ secrets.DATABASE_URL }}
```

---

## 추가 리소스

- [Docker 공식 문서](https://docs.docker.com/)
- [GitHub Actions 문서](https://docs.github.com/en/actions)
- [AWS EC2 문서](https://docs.aws.amazon.com/ec2/)
- [FastAPI 배포 가이드](https://fastapi.tiangolo.com/deployment/)

---

## 문의 및 지원

문제가 발생하면 다음을 확인하세요:
1. GitHub Actions 로그
2. EC2 인스턴스 로그 (`docker-compose logs`)
3. 시스템 리소스 (`htop`, `df -h`)
4. 네트워크 연결 (보안 그룹, 방화벽)

