"""매처 서비스.

RfP 요구사항과 제안서 섹션을 매칭합니다.
"""

from __future__ import annotations

from typing import List, Tuple

from app.domain.rfp.schemas import Requirement
from app.domain.proposal.schemas import ProposalSection, ProposalDocument
from app.domain.evaluation.schemas.evaluation_schema import (
    RequirementMatch,
    MatchStatus,
    EvaluationScore,
)


class Matcher:
    """요구사항-제안서 매처."""
    
    def __init__(self, similarity_threshold: float = 0.6):
        """
        Args:
            similarity_threshold: 유사도 임계값 (0-1)
        """
        self.similarity_threshold = similarity_threshold
    
    def match_requirement(
        self,
        requirement: Requirement,
        proposal: ProposalDocument
    ) -> RequirementMatch:
        """요구사항을 제안서와 매칭합니다.
        
        Args:
            requirement: RfP 요구사항
            proposal: 제안서 문서
            
        Returns:
            매칭 결과
        """
        # 제안서 섹션에서 관련 섹션 찾기
        matched_sections = self._find_matching_sections(
            requirement,
            proposal.sections
        )
        
        # 매칭 상태 판단
        status = self._determine_match_status(
            requirement,
            matched_sections
        )
        
        # 점수 계산
        score = self._calculate_score(status, matched_sections)
        score_category = self._get_score_category(score)
        
        # 분석 생성
        analysis = self._generate_analysis(
            requirement,
            matched_sections,
            status
        )
        
        return RequirementMatch(
            requirement_id=requirement.id,
            requirement_title=requirement.title,
            requirement_priority=requirement.priority.value,
            status=status,
            matched_sections=[s.id for s, _ in matched_sections],
            score=score,
            score_category=score_category,
            analysis=analysis,
            gaps=[],  # LLM으로 분석 가능
            strengths=[],  # LLM으로 분석 가능
        )
    
    def _find_matching_sections(
        self,
        requirement: Requirement,
        sections: List[ProposalSection]
    ) -> List[Tuple[ProposalSection, float]]:
        """요구사항과 매칭되는 섹션을 찾습니다.
        
        Returns:
            (섹션, 유사도) 튜플 리스트
        """
        matched = []
        
        for section in sections:
            # 키워드 기반 유사도 계산 (간단한 버전)
            similarity = self._calculate_keyword_similarity(
                requirement,
                section
            )
            
            if similarity >= self.similarity_threshold:
                matched.append((section, similarity))
        
        # 유사도 높은 순으로 정렬
        matched.sort(key=lambda x: x[1], reverse=True)
        
        return matched[:3]  # 최대 3개
    
    def _calculate_keyword_similarity(
        self,
        requirement: Requirement,
        section: ProposalSection
    ) -> float:
        """키워드 기반 유사도를 계산합니다."""
        
        # 요구사항 키워드
        req_keywords = set(requirement.keywords)
        req_words = set(requirement.title.lower().split() + 
                       requirement.description.lower().split())
        req_keywords.update(req_words)
        
        # 섹션 키워드
        section_words = set(section.title.lower().split() + 
                          section.content.lower().split())
        
        # Jaccard 유사도
        if not req_keywords or not section_words:
            return 0.0
        
        intersection = req_keywords.intersection(section_words)
        union = req_keywords.union(section_words)
        
        return len(intersection) / len(union) if union else 0.0
    
    def _determine_match_status(
        self,
        requirement: Requirement,
        matched_sections: List[Tuple[ProposalSection, float]]
    ) -> MatchStatus:
        """매칭 상태를 판단합니다."""
        
        if not matched_sections:
            return MatchStatus.NOT_ADDRESSED
        
        # 최고 유사도로 판단
        best_similarity = matched_sections[0][1]
        
        if best_similarity >= 0.8:
            return MatchStatus.FULLY_MATCHED
        elif best_similarity >= 0.6:
            return MatchStatus.PARTIALLY_MATCHED
        else:
            return MatchStatus.NOT_MATCHED
    
    def _calculate_score(
        self,
        status: MatchStatus,
        matched_sections: List[Tuple[ProposalSection, float]]
    ) -> float:
        """점수를 계산합니다."""
        
        if status == MatchStatus.NOT_ADDRESSED:
            return 0.0
        elif status == MatchStatus.NOT_MATCHED:
            return 30.0
        elif status == MatchStatus.PARTIALLY_MATCHED:
            # 유사도에 따라 50-79점
            if matched_sections:
                similarity = matched_sections[0][1]
                return 50 + (similarity - 0.6) * (29 / 0.2)
            return 50.0
        else:  # FULLY_MATCHED
            # 유사도에 따라 80-100점
            if matched_sections:
                similarity = matched_sections[0][1]
                return 80 + (similarity - 0.8) * (20 / 0.2)
            return 80.0
    
    def _get_score_category(self, score: float) -> EvaluationScore:
        """점수 카테고리를 반환합니다."""
        if score >= 90:
            return EvaluationScore.EXCELLENT
        elif score >= 70:
            return EvaluationScore.GOOD
        elif score >= 50:
            return EvaluationScore.FAIR
        elif score >= 30:
            return EvaluationScore.POOR
        else:
            return EvaluationScore.VERY_POOR
    
    def _generate_analysis(
        self,
        requirement: Requirement,
        matched_sections: List[Tuple[ProposalSection, float]],
        status: MatchStatus
    ) -> str:
        """간단한 분석을 생성합니다."""
        
        if status == MatchStatus.NOT_ADDRESSED:
            return f"요구사항 '{requirement.title}'에 대한 내용이 제안서에 없습니다."
        
        if not matched_sections:
            return "매칭된 섹션이 없습니다."
        
        section, similarity = matched_sections[0]
        
        if status == MatchStatus.FULLY_MATCHED:
            return f"제안서 섹션 '{section.title}'에서 요구사항을 충분히 다루고 있습니다."
        elif status == MatchStatus.PARTIALLY_MATCHED:
            return f"제안서 섹션 '{section.title}'에서 요구사항을 부분적으로 다루고 있습니다."
        else:
            return f"제안서에서 요구사항을 충분히 다루지 못했습니다."
