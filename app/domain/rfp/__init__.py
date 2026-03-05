"""RfP 도메인.

RfP(Request for Proposal) 문서 처리를 담당합니다.

주요 기능:
- PDF에서 RfP 문서 파싱
- 요구사항 추출 및 분류
- 평가 기준 추출
- 요구사항 저장 및 조회
"""

from app.domain.rfp.schemas import (
    RequirementType,
    RequirementPriority,
    Requirement,
    EvaluationCriteria,
    RfPMetadata,
    RfPDocument,
    RequirementExtractionRequest,
    RequirementExtractionResponse,
)

from app.domain.rfp.parsers import (
    RfPPDFParser,
    RequirementExtractor,
)

from app.domain.rfp.repositories import (
    RequirementRepository,
    RfPDocumentRepository,
)

from app.domain.rfp.services import (
    RfPService,
)

__all__ = [
    # Schemas
    "RequirementType",
    "RequirementPriority",
    "Requirement",
    "EvaluationCriteria",
    "RfPMetadata",
    "RfPDocument",
    "RequirementExtractionRequest",
    "RequirementExtractionResponse",
    # Parsers
    "RfPPDFParser",
    "RequirementExtractor",
    # Repositories
    "RequirementRepository",
    "RfPDocumentRepository",
    # Services
    "RfPService",
]
