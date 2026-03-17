"""ODA 용어사전 라우터

용어 검색 및 조회 API 엔드포인트를 제공합니다.
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from domain.terms.models.oda_term import ODATermEntry
from domain.terms.services.term_service import TermService

router = APIRouter(prefix="/api/v1/term", tags=["term"])

# 전역 서비스 인스턴스 (애플리케이션 시작 시 초기화)
_term_service: Optional[TermService] = None


def get_term_service() -> TermService:
    """용어사전 서비스 인스턴스 반환"""
    global _term_service
    if _term_service is None:
        _term_service = TermService()
    return _term_service


# Request/Response 모델
class TermSearchRequest(BaseModel):
    """용어 검색 요청"""

    query: str = Field(..., description="검색어")
    limit: int = Field(10, ge=1, le=100, description="최대 결과 수")
    search_type: Optional[str] = Field("all", description="검색 타입: 'title'(제목), 'content'(내용), 'all'(전체)")


class TermResponse(BaseModel):
    """용어 응답"""

    korean_name: str = Field(..., description="한글명")
    english_name: Optional[str] = Field(None, description="영문명")
    abbreviation: Optional[str] = Field(None, description="약어")
    description: str = Field(..., description="설명")
    instruction: str = Field(..., description="지시사항")
    input: str = Field(..., description="입력 텍스트")
    output: str = Field(..., description="출력 텍스트")

    @classmethod
    def from_entry(cls, entry: ODATermEntry) -> "TermResponse":
        """ODATermEntry에서 TermResponse 생성"""
        parsed = entry.parsed_output
        return cls(
            korean_name=parsed.korean_name,
            english_name=parsed.english_name,
            abbreviation=parsed.abbreviation,
            description=parsed.description,
            instruction=entry.instruction,
            input=entry.input,
            output=entry.output,
        )


class TermSearchResponse(BaseModel):
    """용어 검색 응답"""

    results: list[TermResponse] = Field(..., description="검색 결과")
    total: int = Field(..., description="전체 결과 수")
    query: str = Field(..., description="검색어")


class TermListResponse(BaseModel):
    """용어 목록 응답"""

    terms: list[TermResponse] = Field(..., description="용어 목록")
    total: int = Field(..., description="전체 용어 수")


# API 엔드포인트
@router.post("/search", response_model=TermSearchResponse)
async def search_terms(
    request: Request,
    search_request: TermSearchRequest,
) -> TermSearchResponse:
    """용어 검색

    한글명, 영문명, 약어, 설명에서 검색어를 찾습니다.

    Args:
        request: FastAPI request object
        search_request: 검색 요청

    Returns:
        검색 결과

    Raises:
        HTTPException: 검색어가 비어있거나 오류 발생 시
    """
    # 프론트엔드에서 넘어온 검색어 출력
    print(f"🔍 [용어 검색] 프론트엔드에서 받은 검색어: '{search_request.query}'")
    print(f"📊 [용어 검색] 최대 결과 수: {search_request.limit}")

    if not search_request.query.strip():
        raise HTTPException(status_code=400, detail="검색어가 비어있습니다")

    try:
        service = get_term_service()
        entries = service.search_terms(
            query=search_request.query,
            limit=search_request.limit,
            search_type=search_request.search_type or "all",
        )

        print(f"✅ [용어 검색] 검색 완료: {len(entries)}개 결과 발견")

        results = [TermResponse.from_entry(entry) for entry in entries]

        return TermSearchResponse(
            results=results,
            total=len(results),
            query=search_request.query,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"검색 중 오류 발생: {str(e)}")


@router.get("/", response_model=TermListResponse)
async def list_terms(
    request: Request,
    limit: Optional[int] = None,
) -> TermListResponse:
    """용어 목록 조회

    Args:
        request: FastAPI request object
        limit: 최대 결과 수 (None이면 전체)

    Returns:
        용어 목록

    Raises:
        HTTPException: 오류 발생 시
    """
    try:
        service = get_term_service()
        entries = service.get_all_terms(limit=limit)
        total = service.get_total_count()

        terms = [TermResponse.from_entry(entry) for entry in entries]

        return TermListResponse(terms=terms, total=total)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"조회 중 오류 발생: {str(e)}")


@router.get("/korean/{name}", response_model=TermResponse)
async def get_term_by_korean_name(
    request: Request,
    name: str,
) -> TermResponse:
    """한글명으로 용어 조회

    Args:
        request: FastAPI request object
        name: 한글명

    Returns:
        용어 정보

    Raises:
        HTTPException: 용어를 찾을 수 없을 때
    """
    try:
        service = get_term_service()
        entry = service.get_term_by_korean_name(name)

        if entry is None:
            raise HTTPException(status_code=404, detail=f"한글명 '{name}'에 해당하는 용어를 찾을 수 없습니다")

        return TermResponse.from_entry(entry)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"조회 중 오류 발생: {str(e)}")


@router.get("/english/{name}", response_model=TermResponse)
async def get_term_by_english_name(
    request: Request,
    name: str,
) -> TermResponse:
    """영문명으로 용어 조회

    Args:
        request: FastAPI request object
        name: 영문명

    Returns:
        용어 정보

    Raises:
        HTTPException: 용어를 찾을 수 없을 때
    """
    try:
        service = get_term_service()
        entry = service.get_term_by_english_name(name)

        if entry is None:
            raise HTTPException(status_code=404, detail=f"영문명 '{name}'에 해당하는 용어를 찾을 수 없습니다")

        return TermResponse.from_entry(entry)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"조회 중 오류 발생: {str(e)}")


@router.get("/abbreviation/{abbr}", response_model=TermResponse)
async def get_term_by_abbreviation(
    request: Request,
    abbr: str,
) -> TermResponse:
    """약어로 용어 조회

    Args:
        request: FastAPI request object
        abbr: 약어

    Returns:
        용어 정보

    Raises:
        HTTPException: 용어를 찾을 수 없을 때
    """
    try:
        service = get_term_service()
        entry = service.get_term_by_abbreviation(abbr)

        if entry is None:
            raise HTTPException(status_code=404, detail=f"약어 '{abbr}'에 해당하는 용어를 찾을 수 없습니다")

        return TermResponse.from_entry(entry)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"조회 중 오류 발생: {str(e)}")
