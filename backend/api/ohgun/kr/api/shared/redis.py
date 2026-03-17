"""Upstash Redis 설정 및 로그인/BullMQ 통신 유틸리티.

이 모듈은:
- 환경변수 `UPSTASH_REDIS_REST_URL`, `UPSTASH_REDIS_REST_TOKEN` 으로 Redis 클라이언트를 생성하고
- 로그인 시 JWT access token을 Redis에 저장하는 헬퍼
- BullMQ(노드 쪽)와 통신하기 위한 큐(push) 헬퍼
를 제공합니다.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

from upstash_redis import Redis


# ---------------------------------------------------------------------------
# Redis 클라이언트 생성 (Upstash REST)
# ---------------------------------------------------------------------------

REDIS_URL: str = os.getenv("UPSTASH_REDIS_REST_URL", "")
REDIS_TOKEN: str = os.getenv("UPSTASH_REDIS_REST_TOKEN", "")

if not REDIS_URL or not REDIS_TOKEN:
    # 개발 편의를 위한 경고 출력만 하고, 실제 요청 시 에러가 발생하도록 둔다.
    # (테스트 환경에서 Redis를 사용하지 않을 수도 있으므로)
    print("⚠️  UPSTASH_REDIS_REST_URL 또는 UPSTASH_REDIS_REST_TOKEN 이 설정되지 않았습니다.")

redis = Redis(url=REDIS_URL, token=REDIS_TOKEN)


# ---------------------------------------------------------------------------
# 키 네이밍 컨벤션
# ---------------------------------------------------------------------------

# JWT access token 저장 키 프리픽스
AUTH_ACCESS_PREFIX = "auth:access:"  # auth:access:<user_id> → JWT access token

# BullMQ(노드)에서 구독할 큐 이름
# 예: Node 쪽에서 new Queue('login-events') 로 생성
BULLMQ_LOGIN_QUEUE_KEY = "bull:login-events"

# 임베딩 배치 작업 큐
BULLMQ_EMBEDDING_QUEUE_KEY = "bull:embedding-jobs"
# 임베딩 작업 상태 키 (job_id → status)
EMBEDDING_JOB_STATUS_PREFIX = "embedding:job:"


# ---------------------------------------------------------------------------
# JWT Access Token 저장/조회 유틸
# ---------------------------------------------------------------------------

def store_access_token(
    user_id: str,
    access_token: str,
    ttl_seconds: int,
) -> None:
    """로그인 시 JWT access token을 Redis에 저장.

    Args:
        user_id: 사용자 식별자 (예: DB user.id 또는 email 등)
        access_token: 발급된 JWT access token (문자열)
        ttl_seconds: 토큰 만료 시간(초). JWT exp와 동일하게 두는 것을 권장.
    """
    key = AUTH_ACCESS_PREFIX + user_id
    # Upstash Redis Python SDK는 ex(초 단위 만료) 파라미터를 지원한다.
    redis.set(key, access_token, ex=ttl_seconds)


def get_access_token(user_id: str) -> Optional[str]:
    """Redis에 저장된 사용자의 JWT access token 조회."""
    key = AUTH_ACCESS_PREFIX + user_id
    value = redis.get(key)
    if value is None:
        return None
    # Upstash 클라이언트는 문자열을 그대로 반환한다.
    return str(value)


def revoke_access_token(user_id: str) -> None:
    """로그아웃 시 토큰을 무효화 (Redis 키 삭제)."""
    key = AUTH_ACCESS_PREFIX + user_id
    redis.delete(key)


# ---------------------------------------------------------------------------
# BullMQ 와의 통신 (로그인 이벤트를 큐에 push)
# ---------------------------------------------------------------------------

def enqueue_login_event(
    user_id: str,
    access_token: str,
    meta: Optional[Dict[str, Any]] = None,
) -> None:
    """로그인 이벤트를 BullMQ 큐로 전달.

    Node/BullMQ 측 예시:
        const queue = new Queue('login-events', { connection: { ...UpstashRedis 연결... }});
        const job = await queue.getNextJob(); // 또는 queue.process(...)

    Args:
        user_id: 로그인한 사용자 ID
        access_token: JWT access token (필요 시 노드 쪽에서 사용)
        meta: 부가 정보 (IP, user-agent 등)
    """
    payload = {
        "user_id": user_id,
        "access_token": access_token,
        "meta": meta or {},
    }
    # BullMQ는 Redis 리스트/스트림/Sorted Set 등 다양한 자료구조를 사용할 수 있지만,
    # 여기서는 간단히 리스트 기반 큐 패턴을 사용한다.
    # Node 쪽에서 동일한 키(BULLMQ_LOGIN_QUEUE_KEY)에 대해 LPOP/RPOP 또는
    # BullMQ의 Redis connection 설정을 이 키에 맞춰 사용하면 된다.
    redis.rpush(BULLMQ_LOGIN_QUEUE_KEY, json.dumps(payload, ensure_ascii=False))


def enqueue_embedding_job(
    domain: str,
    entity_type: str,
    job_id: str,
    limit: Optional[int] = None,
    add: Optional[bool] = None,
) -> None:
    """임베딩 배치 작업을 BullMQ 큐에 추가.

    Args:
        domain: 도메인 (예: "koica")
        entity_type: 엔티티 타입 (예: "project", "report")
        job_id: 작업 고유 ID (중복 방지용)
        limit: 최대 처리 건수 (None이면 전체)
        add: True면 기존 임베딩 유지, 미존재만 추가. None/False면 전체 삭제 후 재생성.
    """
    payload: Dict[str, Any] = {
        "job_id": job_id,
        "domain": domain,
        "entity_type": entity_type,
        "limit": limit,
        "status": "pending",
    }
    if add is not None:
        payload["add"] = add
    redis.rpush(BULLMQ_EMBEDDING_QUEUE_KEY, json.dumps(payload, ensure_ascii=False))
    # 작업 상태 초기화
    redis.set(EMBEDDING_JOB_STATUS_PREFIX + job_id, "pending", ex=3600)  # 1시간 TTL


def get_embedding_job_status(job_id: str) -> Optional[str]:
    """임베딩 작업 상태 조회 (pending, running, completed, failed)."""
    key = EMBEDDING_JOB_STATUS_PREFIX + job_id
    value = redis.get(key)
    return str(value) if value is not None else None


def update_embedding_job_status(job_id: str, status: str, ttl_seconds: int = 3600) -> None:
    """임베딩 작업 상태 업데이트."""
    key = EMBEDDING_JOB_STATUS_PREFIX + job_id
    redis.set(key, status, ex=ttl_seconds)


def check_redis_token_valid() -> bool:
    """Upstash Redis 토큰 유효성 확인 (간단한 ping)."""
    try:
        redis.ping()
        return True
    except Exception:
        return False


__all__ = [
    "redis",
    "store_access_token",
    "get_access_token",
    "revoke_access_token",
    "enqueue_login_event",
    "enqueue_embedding_job",
    "get_embedding_job_status",
    "update_embedding_job_status",
    "check_redis_token_valid",
    "BULLMQ_EMBEDDING_QUEUE_KEY",
]

