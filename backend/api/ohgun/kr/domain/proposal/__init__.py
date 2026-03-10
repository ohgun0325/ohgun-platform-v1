"""Proposal 도메인.

제안서(Proposal) 문서 처리를 담당합니다.

주요 기능:
- PDF에서 제안서 파싱
- 목차(TOC) 추출
- 섹션 구조화
"""

from app.domain.proposal.schemas import (
    SectionType,
    ProposalSection,
    TableOfContents,
    TOCEntry,
    ProposalMetadata,
    ProposalDocument,
    ProposalParsingRequest,
    ProposalParsingResponse,
)

from app.domain.proposal.parsers import (
    ProposalPDFParser,
)

from app.domain.proposal.services import (
    ProposalService,
)

__all__ = [
    # Schemas
    "SectionType",
    "ProposalSection",
    "TableOfContents",
    "TOCEntry",
    "ProposalMetadata",
    "ProposalDocument",
    "ProposalParsingRequest",
    "ProposalParsingResponse",
    # Parsers
    "ProposalPDFParser",
    # Services
    "ProposalService",
]
