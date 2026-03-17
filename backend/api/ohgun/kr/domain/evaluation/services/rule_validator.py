"""규칙 검증기.

제안서가 RfP의 규칙을 준수하는지 검증합니다.
"""

from __future__ import annotations

from typing import List

from domain.rfp.schemas import RfPDocument
from domain.proposal.schemas import ProposalDocument
from domain.evaluation.schemas.evaluation_schema import RuleValidationResult


class RuleValidator:
    """규칙 검증기."""
    
    def validate_all(
        self,
        rfp: RfPDocument,
        proposal: ProposalDocument
    ) -> List[RuleValidationResult]:
        """모든 규칙을 검증합니다.
        
        Args:
            rfp: RfP 문서
            proposal: 제안서 문서
            
        Returns:
            검증 결과 리스트
        """
        results = []
        
        # 페이지 수 검증
        results.append(self._validate_page_count(rfp, proposal))
        
        # 제출 기한 검증 (메타데이터에 있을 경우)
        # results.append(self._validate_submission_deadline(rfp, proposal))
        
        # 필수 섹션 검증
        results.append(self._validate_required_sections(rfp, proposal))
        
        return results
    
    def _validate_page_count(
        self,
        rfp: RfPDocument,
        proposal: ProposalDocument
    ) -> RuleValidationResult:
        """페이지 수를 검증합니다."""
        
        # RfP에서 최대 페이지 수 추출 (간단한 구현)
        max_pages = 150  # 기본값
        
        proposal_pages = proposal.metadata.total_pages or 0
        
        if proposal_pages <= max_pages:
            return RuleValidationResult(
                rule_id="RULE-PAGE-001",
                rule_description=f"제안서는 {max_pages}페이지 이하여야 함",
                passed=True,
                severity="high",
                message="페이지 수 요구사항 충족",
                details=f"제안서: {proposal_pages}페이지 / 최대: {max_pages}페이지"
            )
        else:
            return RuleValidationResult(
                rule_id="RULE-PAGE-001",
                rule_description=f"제안서는 {max_pages}페이지 이하여야 함",
                passed=False,
                severity="high",
                message="페이지 수 초과",
                details=f"제안서: {proposal_pages}페이지 / 최대: {max_pages}페이지"
            )
    
    def _validate_required_sections(
        self,
        rfp: RfPDocument,
        proposal: ProposalDocument
    ) -> RuleValidationResult:
        """필수 섹션을 검증합니다."""
        
        # 필수 섹션 타입
        required_types = ["executive_summary", "approach", "budget", "timeline"]
        
        proposal_types = {section.type.value for section in proposal.sections}
        
        missing_types = [t for t in required_types if t not in proposal_types]
        
        if not missing_types:
            return RuleValidationResult(
                rule_id="RULE-SECTION-001",
                rule_description="필수 섹션 포함 여부",
                passed=True,
                severity="critical",
                message="모든 필수 섹션 포함됨",
                details=f"필수 섹션: {', '.join(required_types)}"
            )
        else:
            return RuleValidationResult(
                rule_id="RULE-SECTION-001",
                rule_description="필수 섹션 포함 여부",
                passed=False,
                severity="critical",
                message="필수 섹션 누락",
                details=f"누락된 섹션: {', '.join(missing_types)}"
            )
