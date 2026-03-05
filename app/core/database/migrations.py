"""
Alembic 마이그레이션 관리
soccer 도메인 테이블 자동 생성
"""
import os
import sys
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine, inspect

from app.core.config import settings
# Soccer 모델들이 사용하는 Base import
from app.domain.soccer.models.bases import Base


def get_alembic_config() -> Config:
    """Alembic 설정 파일 생성 및 반환."""
    # 프로젝트 루트 경로
    project_root = Path(__file__).parent.parent.parent.absolute()
    alembic_dir = project_root / "alembic"
    alembic_ini_path = project_root / "alembic.ini"
    
    # alembic 디렉토리 생성
    alembic_dir.mkdir(exist_ok=True)
    versions_dir = alembic_dir / "versions"
    versions_dir.mkdir(exist_ok=True)
    
    # versions/__init__.py 파일 생성 (없는 경우)
    versions_init = versions_dir / "__init__.py"
    if not versions_init.exists():
        versions_init.write_text("", encoding="utf-8")
    
    # alembic.ini 파일 생성 (없는 경우)
    if not alembic_ini_path.exists():
        alembic_cfg = Config()
        alembic_cfg.set_main_option("script_location", str(alembic_dir))
        alembic_cfg.set_main_option("sqlalchemy.url", settings.get_database_url())
        alembic_cfg.set_main_option("file_template", "%%(year)d%%(month).2d%%(day).2d_%%(hour).2d%%(minute).2d_%%(rev)s_%%(slug)s")
        
        # alembic.ini 파일로 저장
        with open(alembic_ini_path, "w", encoding="utf-8") as f:
            f.write(f"""[alembic]
script_location = {alembic_dir}
prepend_sys_path = .
sqlalchemy.url = {settings.get_database_url()}
file_template = %%(year)d%%(month).2d%%(day).2d_%%(hour).2d%%(minute).2d_%%(rev)s_%%(slug)s

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
""")
    
    # Alembic Config 객체 생성
    alembic_cfg = Config(str(alembic_ini_path))
    alembic_cfg.set_main_option("script_location", str(alembic_dir))
    alembic_cfg.set_main_option("sqlalchemy.url", settings.get_database_url())
    
    return alembic_cfg


def init_alembic_if_needed():
    """Alembic 초기화 (env.py, script.py.mako가 없는 경우에만)."""
    project_root = Path(__file__).parent.parent.parent.absolute()
    alembic_dir = project_root / "alembic"
    env_py = alembic_dir / "env.py"
    script_py_mako = alembic_dir / "script.py.mako"
    
    if not env_py.exists():
        # env.py 생성
        with open(env_py, "w", encoding="utf-8") as f:
            f.write('''"""Alembic 환경 설정."""
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

# Base 메타데이터 import (모든 모델이 등록되도록)
from app.domain.soccer.models.bases import Base
# Soccer 도메인 모델 import (테이블이 등록되도록)
from app.domain.soccer.models.bases import players, schedules, stadium, teams

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
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
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
''')
    
    if not script_py_mako.exists():
        # script.py.mako 생성
        with open(script_py_mako, "w", encoding="utf-8") as f:
            f.write('''"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

"""
from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

# revision identifiers, used by Alembic.
revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
branch_labels = ${repr(branch_labels)}
depends_on = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
''')


def create_soccer_tables_migration():
    """Soccer 테이블을 위한 Alembic 마이그레이션 생성 및 실행."""
    try:
        # Alembic 초기화
        init_alembic_if_needed()
        
        # Alembic 설정 가져오기
        alembic_cfg = get_alembic_config()
        
        # 모델 import (테이블이 Base.metadata에 등록되도록)
        from app.domain.soccer.models.bases import players, schedules, stadium, teams
        
        print("=" * 60)
        print("📦 Soccer 테이블 마이그레이션 시작")
        print("=" * 60)
        
        # 현재 마이그레이션 상태 확인
        script_dir = ScriptDirectory.from_config(alembic_cfg)
        head_revision = script_dir.get_current_head()
        
        if head_revision:
            print(f"현재 HEAD 리비전: {head_revision}")
        else:
            print("초기 마이그레이션 생성 중...")
        
        # 현재 데이터베이스 마이그레이션 상태 확인 (재시도 로직 포함)
        max_retries = 3
        retry_delay = 2
        for attempt in range(max_retries):
            try:
                # 연결 풀 설정으로 안정성 향상
                engine = create_engine(
                    settings.get_database_url(),
                    pool_pre_ping=True,  # 연결 유효성 사전 확인
                    pool_recycle=3600,  # 1시간마다 연결 재생성
                    connect_args={
                        "connect_timeout": 10,
                        "sslmode": "require",
                    }
                )
                with engine.connect() as conn:
                    context = MigrationContext.configure(conn)
                    current_rev = context.get_current_revision()
                    
                    if current_rev is None:
                        print("데이터베이스에 마이그레이션이 없습니다. 초기 마이그레이션 생성 중...")
                    else:
                        print(f"현재 데이터베이스 리비전: {current_rev}")
                break  # 성공하면 루프 종료
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"⚠️ 데이터베이스 연결 시도 {attempt + 1}/{max_retries} 실패, {retry_delay}초 후 재시도... ({str(e)[:100]})")
                    import time
                    time.sleep(retry_delay)
                else:
                    print(f"⚠️ 데이터베이스 상태 확인 중 오류 (최대 재시도 횟수 초과, 무시하고 계속): {e}")
        
        # 자동 마이그레이션 생성 (변경사항 감지)
        migration_created = False
        try:
            # 변경사항이 있으면 새 마이그레이션 생성
            command.revision(
                alembic_cfg,
                autogenerate=True,
                message="create_or_update_soccer_tables",
            )
            print("✅ 마이그레이션 파일 생성 완료")
            migration_created = True
        except Exception as e:
            error_msg = str(e)
            if "Target database is not up to date" in error_msg:
                print("⚠️ 데이터베이스가 최신 상태가 아닙니다. 먼저 마이그레이션을 적용합니다.")
                # 마이그레이션 적용 시도
                try:
                    command.upgrade(alembic_cfg, "head")
                    print("✅ 기존 마이그레이션 적용 완료")
                except Exception as upgrade_error:
                    print(f"⚠️ 마이그레이션 적용 중 오류: {upgrade_error}")
                    # 마이그레이션 적용 실패 시 더 이상 진행하지 않음
                    return
                
                # 변경사항이 있으면 새 마이그레이션 생성
                try:
                    command.revision(
                        alembic_cfg,
                        autogenerate=True,
                        message="create_or_update_soccer_tables",
                    )
                    print("✅ 마이그레이션 파일 생성 완료")
                    migration_created = True
                except Exception as e2:
                    if "No changes detected" in str(e2):
                        print("✅ 변경사항이 없습니다. 마이그레이션 파일 생성 건너뜀")
                    elif "Can't locate revision identified by" not in str(e2):
                        print(f"⚠️ 마이그레이션 생성 중 오류: {e2}")
            elif "No changes detected" in error_msg:
                print("✅ 변경사항이 없습니다. 마이그레이션 파일 생성 건너뜀")
            else:
                print(f"⚠️ 마이그레이션 생성 중 오류: {e}")
                # 치명적 오류가 아니면 계속 진행
        
        # 마이그레이션 적용 (새 마이그레이션이 생성되었거나 기존 마이그레이션이 있는 경우)
        if migration_created or head_revision:
            print("\n마이그레이션 적용 중...")
            try:
                command.upgrade(alembic_cfg, "head")
                print("✅ 마이그레이션 적용 완료!")
            except Exception as upgrade_error:
                print(f"⚠️ 마이그레이션 적용 중 오류: {upgrade_error}")
                import traceback
                traceback.print_exc()
                # 마이그레이션 실패해도 서버는 계속 실행되도록 예외를 다시 raise하지 않음
                return
        else:
            print("✅ 마이그레이션할 내용이 없습니다.")
        
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ 마이그레이션 실패: {e}")
        import traceback
        traceback.print_exc()
        # 서버가 계속 실행되도록 예외를 다시 raise하지 않음
        return


def apply_soccer_migrations() -> None:
    """
    Soccer 도메인 테이블에 대한 Alembic 마이그레이션을 **적용만** 한다.

    - 새로운 revision을 생성하지 않고, 이미 존재하는 마이그레이션만 `upgrade head`로 적용한다.
    - 스키마 변경이 필요하면 CLI에서 수동으로:
        alembic revision --autogenerate -m "msg"
        alembic upgrade head
      를 실행해야 한다.
    """
    try:
        # Alembic 초기화 (env.py 등 생성)
        init_alembic_if_needed()

        # Alembic 설정 가져오기
        alembic_cfg = get_alembic_config()

        # 모델 import (테이블이 Base.metadata에 등록되도록)
        from app.domain.soccer.models.bases import players, schedules, stadium, teams  # noqa: F401

        print("=" * 60)
        print("📦 Soccer 테이블 Alembic upgrade head 적용 시작")
        print("=" * 60)

        # 현재 HEAD 리비전 정보 출력
        script_dir = ScriptDirectory.from_config(alembic_cfg)
        head_revision = script_dir.get_current_head()
        print(f"현재 HEAD 리비전: {head_revision}")

        # 기존 마이그레이션을 DB에 적용
        command.upgrade(alembic_cfg, "head")
        print("✅ Alembic upgrade head 적용 완료!")
        print("=" * 60)

    except Exception as e:
        print(f"❌ Alembic upgrade head 적용 실패: {e}")
        import traceback
        traceback.print_exc()
        # 서버는 계속 실행되도록 예외를 다시 raise하지 않음
        return
