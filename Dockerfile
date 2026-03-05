# FastAPI LangChain Application Dockerfile (CUDA 지원)
FROM python:3.11-slim

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 종속성 설치 (PostgreSQL 클라이언트 등)
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    postgresql-client \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python 종속성 복사 및 설치
COPY requirements.txt .

# PyTorch CUDA 버전 먼저 설치 (CUDA 12.1 지원)
# docker-compose.yml에서 GPU가 활성화되면 자동으로 CUDA를 사용합니다
RUN pip install --no-cache-dir --upgrade pip && \
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# 나머지 종속성 설치
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY . .

# 모델 디렉토리 생성 (QLoRA 체크포인트용)
RUN mkdir -p models/qlora_checkpoints

# 포트 노출
EXPOSE 8000

# 헬스체크 설정
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 애플리케이션 실행
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
