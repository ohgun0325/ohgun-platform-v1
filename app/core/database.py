"""
데이터베이스 연결 및 세션 관리 (호환성 레이어)
새로운 구조(app.core.database)를 사용하도록 리다이렉트
기존 코드와의 호환성을 위해 유지
"""
import time
from typing import Optional

import psycopg2
from pgvector.psycopg2 import register_vector

from app.core.config import settings

# 새로운 구조로 리다이렉트 (루즈한 결합도 유지)
from app.core.database import (
    Base,
    TimestampMixin,
    SoftDeleteMixin,
    StatusMixin,
    engine,
    AsyncSessionLocal,
    get_db,
    init_database,
    check_migration_status,
    close_database,
    create_database_engine,
)


def wait_for_db(max_retries: int = 10) -> None:
    """Wait for PostgreSQL database to be ready.

    Args:
        max_retries: Maximum number of connection attempts.

    Raises:
        Exception: If database connection fails after max_retries.
    """
    print("🔄 Neon PostgreSQL 데이터베이스 연결 중...")

    for attempt in range(max_retries):
        try:
            # DATABASE_URL이 있으면 사용, 없으면 개별 파라미터 사용
            db_url = settings.get_database_url()
            conn = psycopg2.connect(db_url)
            conn.close()
            print("✅ Neon PostgreSQL 데이터베이스 연결 성공!")
            return
        except psycopg2.OperationalError as e:
            if attempt < max_retries - 1:
                print(f"⏳ 재시도 {attempt + 1}/{max_retries}... ({str(e)[:50]})")
                time.sleep(2)
            else:
                raise Exception(f"데이터베이스 연결 실패: {str(e)}")


def get_db_connection(register_vector_extension: bool = True) -> psycopg2.extensions.connection:
    """Get a new database connection.

    Args:
        register_vector_extension: Whether to register pgvector extension.
                                   Set to False if extension is not installed yet.

    Returns:
        Database connection object.
    """
    # DATABASE_URL이 있으면 사용, 없으면 개별 파라미터 사용
    db_url = settings.get_database_url()
    conn = psycopg2.connect(db_url)

    # Register pgvector extension (only if already installed)
    if register_vector_extension:
        try:
            register_vector(conn)
        except psycopg2.ProgrammingError:
            # Extension not installed yet, will be installed in setup_pgvector
            pass

    return conn


__all__ = [
    # 새로운 구조 (리다이렉트)
    "Base",
    "TimestampMixin",
    "SoftDeleteMixin",
    "StatusMixin",
    "engine",
    "AsyncSessionLocal",
    "get_db",
    "init_database",
    "check_migration_status",
    "close_database",
    "create_database_engine",
    # 기존 함수 (호환성 유지)
    "wait_for_db",
    "get_db_connection",
]

