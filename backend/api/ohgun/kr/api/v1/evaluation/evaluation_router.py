"""Evaluation API 라우터.

RfP 평가 시스템 API를 제공합니다.
"""

from fastapi import APIRouter, File, UploadFile, HTTPException, Form
from typing import Optional

from app.domain.rfp import (
    RfPService,
    RequirementExtractionRequest,
    RequirementExtractionResponse,
)
from app.domain.proposal import (
    ProposalService,
    ProposalParsingResponse,
)
from app.domain.evaluation import (
    EvaluationOrchestrator,
    EvaluationRequest,
    EvaluationResponse,
)

router = APIRouter(prefix="/evaluation", tags=["evaluation"])

# 서비스 인스턴스
rfp_service = RfPService()
proposal_service = ProposalService()
evaluation_orchestrator = EvaluationOrchestrator(rfp_service, proposal_service)


@router.post("/rfp/upload", response_model=RequirementExtractionResponse)
async def upload_rfp_pdf(
    file: UploadFile = File(..., description="RfP PDF 파일"),
    extract_tables: bool = Form(default=True, description="표 추출 여부"),
    use_llm: bool = Form(default=False, description="LLM 사용 여부"),
):
    """RfP PDF를 업로드하고 요구사항을 추출합니다.
    
    Args:
        file: PDF 파일
        extract_tables: 표 추출 여부
        use_llm: LLM 사용 여부
        
    Returns:
        요구사항 추출 결과
    """
    try:
        # PDF 읽기
        pdf_bytes = await file.read()
        
        # 처리
        response = rfp_service.process_rfp_pdf(pdf_bytes, save_to_repo=True)
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"RfP 처리 실패: {str(e)}")


@router.post("/proposal/upload", response_model=ProposalParsingResponse)
async def upload_proposal_pdf(
    file: UploadFile = File(..., description="제안서 PDF 파일"),
    extract_toc: bool = Form(default=True, description="목차 추출 여부"),
    extract_tables: bool = Form(default=True, description="표 추출 여부"),
):
    """제안서 PDF를 업로드하고 파싱합니다.
    
    Args:
        file: PDF 파일
        extract_toc: 목차 추출 여부
        extract_tables: 표 추출 여부
        
    Returns:
        제안서 파싱 결과
    """
    try:
        # PDF 읽기
        pdf_bytes = await file.read()
        
        # 처리
        response = proposal_service.process_proposal_pdf(pdf_bytes)
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"제안서 처리 실패: {str(e)}")


@router.post("/evaluate", response_model=EvaluationResponse)
async def evaluate_proposal(
    request: EvaluationRequest
):
    """제안서를 평가합니다.
    
    Args:
        request: 평가 요청
        
    Returns:
        평가 결과
    """
    try:
        response = evaluation_orchestrator.evaluate(request)
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"평가 실패: {str(e)}")


@router.get("/rfp/{rfp_id}")
async def get_rfp(rfp_id: str):
    """RfP 문서를 조회합니다.
    
    Args:
        rfp_id: RfP ID
        
    Returns:
        RfP 문서
    """
    document = rfp_service.get_rfp_document(rfp_id)
    
    if not document:
        raise HTTPException(status_code=404, detail="RfP를 찾을 수 없습니다")
    
    return document


@router.get("/rfp/{rfp_id}/requirements")
async def get_rfp_requirements(rfp_id: str):
    """RfP의 요구사항을 조회합니다.
    
    Args:
        rfp_id: RfP ID
        
    Returns:
        요구사항 리스트
    """
    requirements = rfp_service.get_requirements(rfp_id)
    
    return {
        "rfp_id": rfp_id,
        "total": len(requirements),
        "requirements": requirements
    }


@router.get("/rfp/{rfp_id}/requirements/mandatory")
async def get_mandatory_requirements(rfp_id: str):
    """필수 요구사항만 조회합니다.
    
    Args:
        rfp_id: RfP ID
        
    Returns:
        필수 요구사항 리스트
    """
    requirements = rfp_service.get_mandatory_requirements(rfp_id)
    
    return {
        "rfp_id": rfp_id,
        "total": len(requirements),
        "requirements": requirements
    }


@router.get("/rfp/{rfp_id}/requirements/search")
async def search_requirements(rfp_id: str, keyword: str):
    """요구사항을 검색합니다.
    
    Args:
        rfp_id: RfP ID
        keyword: 검색 키워드
        
    Returns:
        검색 결과
    """
    requirements = rfp_service.search_requirements(rfp_id, keyword)
    
    return {
        "rfp_id": rfp_id,
        "keyword": keyword,
        "total": len(requirements),
        "requirements": requirements
    }


@router.get("/rfp/{rfp_id}/statistics")
async def get_rfp_statistics(rfp_id: str):
    """RfP 통계를 조회합니다.
    
    Args:
        rfp_id: RfP ID
        
    Returns:
        통계 정보
    """
    stats = rfp_service.get_statistics(rfp_id)
    
    return {
        "rfp_id": rfp_id,
        "statistics": stats
    }


@router.get("/rfps")
async def list_rfps():
    """저장된 모든 RfP를 조회합니다.
    
    Returns:
        RfP ID 리스트
    """
    rfp_ids = rfp_service.list_all_rfps()
    
    return {
        "total": len(rfp_ids),
        "rfp_ids": rfp_ids
    }
