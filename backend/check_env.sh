#!/bin/bash
# EC2 우분투 환경에서 .env 파일을 확인하는 스크립트

echo "=================================================="
echo "   .env 파일 확인 스크립트"
echo "=================================================="
echo ""

# 작업 디렉토리 확인
if [ -f "/home/ubuntu/langchain/.env" ]; then
  ENV_PATH="/home/ubuntu/langchain/.env"
elif [ -f "$HOME/langchain/.env" ]; then
  ENV_PATH="$HOME/langchain/.env"
elif [ -f ".env" ]; then
  ENV_PATH=".env"
else
  echo "❌ .env 파일을 찾을 수 없습니다"
  echo ""
  echo "검색한 경로:"
  echo "  - /home/ubuntu/langchain/.env"
  echo "  - $HOME/langchain/.env"
  echo "  - ./.env"
  exit 1
fi

echo "✅ .env 파일 위치: $ENV_PATH"
echo ""

# 파일 정보
echo "=== 파일 정보 ==="
echo "크기: $(wc -c < "$ENV_PATH") bytes"
echo "라인 수: $(wc -l < "$ENV_PATH") 줄"
echo "수정 시간: $(stat -c %y "$ENV_PATH" 2>/dev/null || stat -f "%Sm" "$ENV_PATH")"
echo ""

# 환경 변수 키 목록 (주석 및 빈 줄 제외)
echo "=== 설정된 환경 변수 목록 ==="
grep -v '^#' "$ENV_PATH" | grep -v '^$' | cut -d'=' -f1 | sort | nl
echo ""

# 주요 설정 값 확인 (민감 정보는 존재 여부만 표시)
echo "=== 주요 설정 값 확인 ==="

# Database 설정
echo "📦 Database Configuration:"
if grep -q '^DATABASE_URL=' "$ENV_PATH"; then
  echo "  DATABASE_URL: ✅ 설정됨"
else
  echo "  DATABASE_URL: ❌ 설정 안됨"
fi

if grep -q '^POSTGRES_HOST=' "$ENV_PATH"; then
  echo "  POSTGRES_HOST: $(grep '^POSTGRES_HOST=' "$ENV_PATH" | cut -d'=' -f2)"
fi

if grep -q '^POSTGRES_PASSWORD=' "$ENV_PATH"; then
  echo "  POSTGRES_PASSWORD: ✅ 설정됨 (***)"
else
  echo "  POSTGRES_PASSWORD: ❌ 설정 안됨"
fi

echo ""

# Gemini API 설정
echo "🤖 Gemini API Configuration:"
if grep -q '^GEMINI_API_KEY=' "$ENV_PATH"; then
  echo "  GEMINI_API_KEY: ✅ 설정됨 (***)"
else
  echo "  GEMINI_API_KEY: ❌ 설정 안됨"
fi

if grep -q '^GEMINI_MODEL=' "$ENV_PATH"; then
  echo "  GEMINI_MODEL: $(grep '^GEMINI_MODEL=' "$ENV_PATH" | cut -d'=' -f2)"
fi

echo ""

# 모델 설정
echo "🔧 Model Configuration:"
echo "  USE_QLORA: $(grep '^USE_QLORA=' "$ENV_PATH" | cut -d'=' -f2 || echo 'not set')"
echo "  MODEL_DEVICE: $(grep '^MODEL_DEVICE=' "$ENV_PATH" | cut -d'=' -f2 || echo 'not set')"
echo "  MODEL_DTYPE: $(grep '^MODEL_DTYPE=' "$ENV_PATH" | cut -d'=' -f2 || echo 'not set')"

echo ""

# Application 설정
echo "⚙️  Application Settings:"
echo "  CORS_ORIGINS: $(grep '^CORS_ORIGINS=' "$ENV_PATH" | cut -d'=' -f2 || echo 'not set')"
if grep -q '^APP_TITLE=' "$ENV_PATH"; then
  echo "  APP_TITLE: $(grep '^APP_TITLE=' "$ENV_PATH" | cut -d'=' -f2)"
fi

echo ""
echo "=================================================="
echo ""

# 전체 내용 표시 옵션 (--show-all 플래그)
if [ "$1" = "--show-all" ]; then
  echo "=== .env 파일 전체 내용 (민감 정보 마스킹) ==="
  cat "$ENV_PATH" | sed -E 's/(PASSWORD|KEY|SECRET)=.*/\1=***MASKED***/g'
  echo ""
fi

# 전체 내용 표시 (마스킹 없음, 주의!)
if [ "$1" = "--show-raw" ]; then
  echo "⚠️  경고: 민감 정보가 포함된 전체 내용을 표시합니다!"
  echo "=== .env 파일 전체 내용 (RAW) ==="
  cat "$ENV_PATH"
  echo ""
fi

echo "💡 사용법:"
echo "  - 기본 정보 확인: ./check_env.sh"
echo "  - 전체 내용 (마스킹): ./check_env.sh --show-all"
echo "  - 전체 내용 (RAW): ./check_env.sh --show-raw"
echo ""

