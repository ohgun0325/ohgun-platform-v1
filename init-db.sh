#!/bin/bash
set -e

# PostgreSQL이 완전히 시작될 때까지 대기
until pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"; do
  echo "PostgreSQL이 시작될 때까지 대기 중..."
  sleep 1
done

# pgvector 확장 활성화
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE EXTENSION IF NOT EXISTS vector;
EOSQL

echo "✅ pgvector 확장이 활성화되었습니다."

