"""평가 오케스트레이터.

전체 평가 프로세스를 조율합니다.
"""

from __future__ import annotations

from typing import Optional

from app.domain.rfp.schemas import RfPDocument
from app.domain.rfp.services import RfPService
from app.domain.proposal.schemas import ProposalDocument
from app.domain.proposal.services import ProposalService
from app.domain.evaluation.schemas.evaluation_schema import (
    EvaluationRequest,
    EvaluationResponse,
    EvaluationReport,
)
from app.domain.evaluation.services.matcher import Matcher
from app.domain.evaluation.services.rule_validator import RuleValidator
from app.domain.evaluation.services.report_generator import ReportGenerator


class EvaluationOrchestrator:
    """평가 오케스트레이터."""
    
    def __init__(
        self,
        rfp_service: Optional[RfPService] = None,
        proposal_service: Optional[ProposalService] = None,
    ):
        """
        Args:
            rfp_service: RfP 서비스
            proposal_service: 제안서 서비스
        """
        self.rfp_service = rfp_service or RfPService()
        self.proposal_service = proposal_service or ProposalService()
        
        self.matcher = Matcher()
        self.rule_validator = RuleValidator()
        self.report_generator = ReportGenerator()
    
    def evaluate(
        self,
        request: EvaluationRequest
    ) -> EvaluationResponse:
        """제안서를 평가합니다.
        
        Args:
            request: 평가 요청
            
        Returns:
            평가 응답
        """
        try:
            # 1. RfP 문서 로드
            rfp = self.rfp_service.get_rfp_document(request.rfp_id)
            if not rfp:
                return EvaluationResponse(
                    success=False,
                    message=f"RfP 문서를 찾을 수 없습니다: {request.rfp_id}",
                    report=None
                )
            
            # 2. 제안서 문서 로드 (저장소에서 가져온다고 가정)
            # 실제로는 proposal_service에 load 메서드가 필요
            proposal = self._load_proposal(request.proposal_id)
            if not proposal:
                return EvaluationResponse(
                    success=False,
                    message=f"제안서 문서를 찾을 수 없습니다: {request.proposal_id}",
                    report=None
                )
            
            # 3. 규칙 검증
            validation_results = self.rule_validator.validate_all(rfp, proposal)
            
            # 심각한 규칙 위반이 있는지 확인
            critical_failures = [
                r for r in validation_results
                if not r.passed and r.severity == "critical"
            ]
            
            if critical_failures:
                failure_messages = "\n".join([r.message for r in critical_failures])
                return EvaluationResponse(
                    success=False,
                    message=f"필수 규칙 위반:\n{failure_messages}",
                    report=None
                )
            
            # 4. 요구사항 매칭
            requirement_matches = []
            for requirement in rfp.requirements:
                match = self.matcher.match_requirement(requirement, proposal)
                requirement_matches.append(match)
            
            # 5. 보고서 생성
            report = self.report_generator.generate_report(
                rfp_id=request.rfp_id,
                proposal_id=request.proposal_id,
                requirement_matches=requirement_matches,
                evaluator=request.evaluator or "AI Evaluator"
            )
            
            return EvaluationResponse(
                success=True,
                message="평가 완료",
                report=report
            )
            
        except Exception as e:
            return EvaluationResponse(
                success=False,
                message=f"평가 중 오류 발생: {str(e)}",
                report=None
            )
    
    def _load_proposal(self, proposal_id: str) -> Optional[ProposalDocument]:
        """제안서를 로드합니다 (임시 구현).
        
        실제로는 ProposalService에 저장소 기능이 필요합니다.
        """
        # TODO: ProposalRepository 구현 필요
        return None
    
    def quick_evaluate(
        self,
        rfp: RfPDocument,
        proposal: ProposalDocument,
        evaluator: str = "AI Evaluator"
    ) -> EvaluationReport:
        """빠른 평가 (문서를 직접 전달).
        
        Args:
            rfp: RfP 문서
            proposal: 제안서 문서
            evaluator: 평가자
            
        Returns:
            평가 보고서
        """
        # 규칙 검증
        validation_results = self.rule_validator.validate_all(rfp, proposal)
        
        # 요구사항 매칭
        requirement_matches = []
        for requirement in rfp.requirements:
            match = self.matcher.match_requirement(requirement, proposal)
            requirement_matches.append(match)
        
        # 보고서 생성
        report = self.report_generator.generate_report(
            rfp_id=rfp.metadata.rfp_id,
            proposal_id=proposal.metadata.proposal_id,
            requirement_matches=requirement_matches,
            evaluator=evaluator
        )
        
        return report
