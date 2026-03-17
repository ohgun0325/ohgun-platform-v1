"""공용 SQLAlchemy Base 클래스.

모든 도메인(koica, term 등)의 ORM 모델이 상속하는 베이스입니다.
"""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """프로젝트 공용 SQLAlchemy Declarative Base."""

    pass
