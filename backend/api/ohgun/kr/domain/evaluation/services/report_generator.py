"""보고서 생성기.

평가 결과를 종합하여 보고서를 생성합니다.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Dict
from collections import defaultdict

from domain.evaluation.schemas.evaluation_schema import (
    RequirementMatch,
    CategoryEvaluation,
    EvaluationReport,
    MatchStatus,
)


class ReportGenerator:
    """보고서 생성기."""
    
    def generate_report(
        self,
        rfp_id: str,
        proposal_id: str,
        requirement_matches: List[RequirementMatch],
        evaluator: str = "AI Evaluator"
    ) -> EvaluationReport:
        """평가 보고서를 생성합니다.
        
        Args:
            rfp_id: RfP ID
            proposal_id: 제안서 ID
            requirement_matches: 요구사항 매칭 결과
            evaluator: 평가자
            
        Returns:
            평가 보고서
        """
        
        # 총점 계산
        total_score = self._calculate_total_score(requirement_matches)
        
        # 카테고리별 평가
        category_evaluations = self._generate_category_evaluations(
            requirement_matches
        )
        
        # 종합 분석
        summary = self._generate_summary(total_score, requirement_matches)
        strengths, weaknesses = self._extract_strengths_weaknesses(
            requirement_matches
        )
        recommendations = self._generate_recommendations(requirement_matches)
        
        # 보고서 ID 생성
        report_id = f"EVAL-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        
        return EvaluationReport(
            report_id=report_id,
            rfp_id=rfp_id,
            proposal_id=proposal_id,
            evaluation_date=datetime.now(),
            evaluator=evaluator,
            total_score=total_score,
            max_score=100.0,
            percentage=total_score,
            requirement_matches=requirement_matches,
            category_evaluations=category_evaluations,
            summary=summary,
            strengths=strengths,
            weaknesses=weaknesses,
            recommendations=recommendations,
        )
    
    def _calculate_total_score(
        self,
        matches: List[RequirementMatch]
    ) -> float:
        """총점을 계산합니다."""
        if not matches:
            return 0.0
        
        # 우선순위별 가중치
        priority_weights = {
            "mandatory": 2.0,
            "highly_desirable": 1.5,
            "desirable": 1.0,
            "optional": 0.5,
        }
        
        weighted_sum = 0.0
        weight_sum = 0.0
        
        for match in matches:
            weight = priority_weights.get(match.requirement_priority, 1.0)
            score = match.score or 0.0
            
            weighted_sum += score * weight
            weight_sum += weight
        
        return weighted_sum / weight_sum if weight_sum > 0 else 0.0
    
    def _generate_category_evaluations(
        self,
        matches: List[RequirementMatch]
    ) -> List[CategoryEvaluation]:
        """카테고리별 평가를 생성합니다."""
        
        # 우선순위별 그룹화
        categories: Dict[str, List[RequirementMatch]] = defaultdict(list)
        
        for match in matches:
            category = match.requirement_priority
            categories[category].append(match)
        
        evaluations = []
        
        for category, category_matches in categories.items():
            total = len(category_matches)
            matched = sum(
                1 for m in category_matches
                if m.status in [MatchStatus.FULLY_MATCHED, MatchStatus.PARTIALLY_MATCHED]
            )
            
            avg_score = sum(m.score or 0 for m in category_matches) / total if total > 0 else 0
            
            fully_matched = sum(
                1 for m in category_matches
                if m.status == MatchStatus.FULLY_MATCHED
            )
            partially_matched = sum(
                1 for m in category_matches
                if m.status == MatchStatus.PARTIALLY_MATCHED
            )
            not_matched = sum(
                1 for m in category_matches
                if m.status in [MatchStatus.NOT_MATCHED, MatchStatus.NOT_ADDRESSED]
            )
            
            evaluations.append(CategoryEvaluation(
                category=category,
                total_requirements=total,
                matched_requirements=matched,
                average_score=avg_score,
                max_score=100.0,
                fully_matched_count=fully_matched,
                partially_matched_count=partially_matched,
                not_matched_count=not_matched,
            ))
        
        return evaluations
    
    def _generate_summary(
        self,
        total_score: float,
        matches: List[RequirementMatch]
    ) -> str:
        """종합 요약을 생성합니다."""
        
        total = len(matches)
        fully_matched = sum(
            1 for m in matches
            if m.status == MatchStatus.FULLY_MATCHED
        )
        
        if total_score >= 90:
            grade = "우수"
        elif total_score >= 70:
            grade = "양호"
        elif total_score >= 50:
            grade = "보통"
        else:
            grade = "미흡"
        
        return (
            f"제안서는 전반적으로 {grade}한 수준입니다. "
            f"총 {total}개의 요구사항 중 {fully_matched}개를 완전히 충족했습니다. "
            f"종합 점수는 {total_score:.1f}점입니다."
        )
    
    def _extract_strengths_weaknesses(
        self,
        matches: List[RequirementMatch]
    ) -> tuple[List[str], List[str]]:
        """강점과 약점을 추출합니다."""
        
        strengths = []
        weaknesses = []
        
        # 점수가 높은 항목
        high_score_matches = [m for m in matches if (m.score or 0) >= 85]
        if high_score_matches:
            for match in high_score_matches[:3]:
                strengths.append(f"{match.requirement_title}: {match.analysis}")
        
        # 점수가 낮은 항목
        low_score_matches = [m for m in matches if (m.score or 0) < 50]
        if low_score_matches:
            for match in low_score_matches[:3]:
                weaknesses.append(f"{match.requirement_title}: {match.analysis}")
        
        return strengths, weaknesses
    
    def _generate_recommendations(
        self,
        matches: List[RequirementMatch]
    ) -> List[str]:
        """개선 권고사항을 생성합니다."""
        
        recommendations = []
        
        # 불일치 항목
        not_matched = [
            m for m in matches
            if m.status in [MatchStatus.NOT_MATCHED, MatchStatus.NOT_ADDRESSED]
        ]
        
        if not_matched:
            for match in not_matched[:5]:
                recommendations.append(
                    f"{match.requirement_title}에 대한 내용을 추가하거나 보완하세요."
                )
        
        # 부분 일치 항목
        partial = [
            m for m in matches
            if m.status == MatchStatus.PARTIALLY_MATCHED
        ]
        
        if partial and len(recommendations) < 5:
            for match in partial[:5 - len(recommendations)]:
                recommendations.append(
                    f"{match.requirement_title}에 대한 설명을 더 상세히 작성하세요."
                )
        
        return recommendations
