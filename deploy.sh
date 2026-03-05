#!/bin/bash
# EC2 배포 스크립트 (로컬에서 수동 배포시 사용)

set -e  # 에러 발생시 스크립트 중단

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 변수 설정
EC2_HOST="${EC2_HOST:-your-ec2-host.com}"
EC2_USER="${EC2_USER:-ubuntu}"
REMOTE_DIR="~/langchain"
SSH_KEY="${SSH_KEY:-~/.ssh/id_rsa}"

echo -e "${GREEN}=== LangChain FastAPI 배포 시작 ===${NC}"

# SSH 키 확인
if [ ! -f "$SSH_KEY" ]; then
    echo -e "${RED}❌ SSH 키를 찾을 수 없습니다: $SSH_KEY${NC}"
    exit 1
fi

# EC2 연결 확인
echo -e "${YELLOW}🔍 EC2 연결 확인 중...${NC}"
if ! ssh -i "$SSH_KEY" -o ConnectTimeout=10 "$EC2_USER@$EC2_HOST" "echo 'Connected'" > /dev/null 2>&1; then
    echo -e "${RED}❌ EC2에 연결할 수 없습니다${NC}"
    exit 1
fi
echo -e "${GREEN}✅ EC2 연결 성공${NC}"

# .env 파일 확인
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠️  .env 파일이 없습니다. .env.example을 참고하여 생성하세요.${NC}"
    read -p "계속하시겠습니까? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# 파일 동기화
echo -e "${YELLOW}📦 파일 동기화 중...${NC}"
ssh -i "$SSH_KEY" "$EC2_USER@$EC2_HOST" "mkdir -p $REMOTE_DIR"

rsync -avz --progress \
    --exclude 'libs/' \
    --exclude 'frontend/node_modules/' \
    --exclude '__pycache__/' \
    --exclude '*.pyc' \
    --exclude '.git/' \
    --exclude 'venv/' \
    --exclude '.env' \
    -e "ssh -i $SSH_KEY" \
    ./ "$EC2_USER@$EC2_HOST:$REMOTE_DIR/"

echo -e "${GREEN}✅ 파일 동기화 완료${NC}"

# .env 파일 별도 전송 (있는 경우)
if [ -f ".env" ]; then
    echo -e "${YELLOW}🔐 환경 변수 파일 전송 중...${NC}"
    scp -i "$SSH_KEY" .env "$EC2_USER@$EC2_HOST:$REMOTE_DIR/.env"
fi

# EC2에서 배포 실행
echo -e "${YELLOW}🚀 EC2에서 배포 실행 중...${NC}"
ssh -i "$SSH_KEY" "$EC2_USER@$EC2_HOST" << 'ENDSSH'
cd ~/langchain

# Docker 설치 확인
if ! command -v docker &> /dev/null; then
    echo "Docker 설치 중..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    newgrp docker
fi

# Docker Compose 설치 확인
if ! command -v docker-compose &> /dev/null; then
    echo "Docker Compose 설치 중..."
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
fi

# 기존 컨테이너 중지
echo "기존 컨테이너 중지 중..."
docker-compose down || true

# 이미지 빌드 및 컨테이너 시작
echo "새 컨테이너 시작 중..."
docker-compose up -d --build

# 상태 확인
echo "=== 컨테이너 상태 ==="
docker-compose ps

echo "=== 최근 로그 (50줄) ==="
docker-compose logs --tail=50

ENDSSH

echo -e "${GREEN}✅ 배포 완료!${NC}"

# 헬스체크
echo -e "${YELLOW}🏥 헬스체크 수행 중...${NC}"
sleep 10

if curl -f "http://$EC2_HOST:8000/health" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ 서비스가 정상적으로 실행 중입니다!${NC}"
    echo -e "${GREEN}🌐 API 문서: http://$EC2_HOST:8000/docs${NC}"
else
    echo -e "${RED}⚠️  헬스체크 실패. 로그를 확인하세요.${NC}"
    ssh -i "$SSH_KEY" "$EC2_USER@$EC2_HOST" "cd $REMOTE_DIR && docker-compose logs --tail=100"
fi

echo -e "${GREEN}=== 배포 스크립트 종료 ===${NC}"

