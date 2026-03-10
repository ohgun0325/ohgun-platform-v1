"""User 라우터 - 사용자 요청 처리

규칙 기반 및 정책 기반 분기를 통해 사용자 요청을 처리합니다.
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.domain.admin.orchestrators.user_flow import UserFlow

router = APIRouter(prefix="/api/v1/admin/user", tags=["admin", "user"])

# 전역 UserFlow 인스턴스 (애플리케이션 시작 시 초기화)
_user_flow: Optional[UserFlow] = None


def get_user_flow() -> UserFlow:
    """UserFlow 인스턴스 반환"""
    global _user_flow
    if _user_flow is None:
        _user_flow = UserFlow()
    return _user_flow


# Request/Response 모델
class UserRequest(BaseModel):
    """사용자 요청"""

    message: str = Field(..., min_length=1, description="사용자 메시지")
    user_id: Optional[int] = Field(None, description="사용자 ID")
    context: Optional[dict] = Field(default_factory=dict, description="추가 컨텍스트 정보")


class UserResponse(BaseModel):
    """사용자 응답"""

    response: str = Field(..., description="AI 응답")
    method: str = Field(..., description="사용된 방법 (rule-based 또는 policy-based)")
    sources: list[str] = Field(default_factory=list, description="참고 문서 (선택)")


# API 엔드포인트
@router.post("", response_model=UserResponse)
async def process_user_request(
    request: Request,
    user_request: UserRequest,
) -> UserResponse:
    """사용자 요청 처리

    사용자의 요청을 받아 규칙 기반 또는 정책 기반으로 처리합니다.
    UserFlow 오케스트레이터가 자동으로 적절한 방법을 선택합니다.

    Args:
        request: FastAPI request object
        user_request: 사용자 요청 (메시지, 사용자 ID, 컨텍스트)

    Returns:
        처리된 응답 (규칙 기반 또는 정책 기반)

    Raises:
        HTTPException: 메시지가 비어있거나 처리 중 오류 발생 시
    """
    print(f"👤 [사용자 요청] 받은 메시지: '{user_request.message}'")
    print(f"   사용자 ID: {user_request.user_id}")

    if not user_request.message.strip():
        raise HTTPException(status_code=400, detail="메시지가 비어있습니다")

    try:
        # UserFlow 가져오기
        flow = get_user_flow()

        # 사용자 요청 처리 (규칙/정책 자동 분기)
        print("🔄 [사용자 요청] UserFlow 처리 시작...")
        result = flow.process(
            message=user_request.message,
            user_id=user_request.user_id,
            context=user_request.context,
        )

        print(f"✅ [사용자 요청] 처리 완료 (방법: {result['method']})")

        return UserResponse(
            response=result["response"],
            method=result["method"],
            sources=result.get("sources", []),
        )

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        print(f"❌ [사용자 요청] 오류 발생: {error_msg}")
        raise HTTPException(
            status_code=500,
            detail=f"사용자 요청 처리 중 오류 발생: {error_msg}",
        )
