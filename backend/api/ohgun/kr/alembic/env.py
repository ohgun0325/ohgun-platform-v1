"""Alembic 환경 설정."""
import sys
from pathlib import Path

# app 폴더에서 실행해도 프로젝트 루트(langchain)를 모듈 경로에 추가
_project_root = Path(__file__).resolve().parent.parent.parent
if _project_root not in sys.path:
    sys.path.insert(0, str(_project_root))

from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

# Base 메타데이터 import (모든 모델이 등록되도록)
from domain.soccer.models.bases import Base
# Soccer 도메인 모델 import (테이블이 등록되도록)
from domain.soccer.models.bases import (
    player_embeddings,
    players,
    schedules,
    stadium,
    teams,
)

# Alembic Config 객체
config = context.config

# 로깅 설정
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Base의 메타데이터를 target_metadata로 설정
target_metadata = Base.metadata

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    from sqlalchemy import create_engine

    # 연결 안정성을 위한 설정
    database_url = config.get_main_option("sqlalchemy.url")

    # create_engine을 직접 사용하여 연결 안정성 설정
    connectable = create_engine(
        database_url,
        poolclass=pool.NullPool,
        pool_pre_ping=True,  # 연결 유효성 사전 확인
        pool_recycle=3600,  # 1시간마다 연결 재생성
        connect_args={
            "connect_timeout": 10,
            "sslmode": "require",
        }
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
