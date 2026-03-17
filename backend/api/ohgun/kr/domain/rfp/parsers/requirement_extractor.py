"""LLM 기반 요구사항 추출기.

Gemini를 사용하여 RfP 문서에서 요구사항을 지능적으로 추출합니다.
"""

from __future__ import annotations

import json
from typing import List, Dict, Any, Optional

from domain.rfp.schemas.rfp_schema import (
    Requirement,
    RequirementType,
    RequirementPriority,
)


class RequirementExtractor:
    """LLM 기반 요구사항 추출기."""
    
    def __init__(self, llm_client: Optional[Any] = None):
        """
        Args:
            llm_client: LLM 클라이언트 (Gemini 등)
        """
        self.llm_client = llm_client
    
    async def extract_requirements(
        self, 
        text: str,
        context: Optional[Dict[str, Any]] = None
    ) -> List[Requirement]:
        """텍스트에서 요구사항을 추출합니다.
        
        Args:
            text: 추출할 텍스트
            context: 추가 컨텍스트 (메타데이터 등)
            
        Returns:
            추출된 요구사항 리스트
        """
        if not self.llm_client:
            raise ValueError("LLM 클라이언트가 설정되지 않았습니다.")
        
        # 프롬프트 생성
        prompt = self._create_extraction_prompt(text, context)
        
        # LLM 호출
        response = await self._call_llm(prompt)
        
        # 응답 파싱
        requirements = self._parse_llm_response(response)
        
        return requirements
    
    def _create_extraction_prompt(
        self, 
        text: str, 
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """요구사항 추출 프롬프트를 생성합니다."""
        
        prompt = f"""다음은 RfP(Request for Proposal) 문서의 일부입니다.
이 문서에서 요구사항(Requirements)을 추출하여 JSON 형식으로 반환해주세요.

각 요구사항은 다음 정보를 포함해야 합니다:
- id: 요구사항 고유 ID (REQ-XXX 형식)
- type: 요구사항 타입 (technical, functional, organizational, financial, legal, other)
- priority: 우선순위 (mandatory, highly_desirable, desirable, optional)
- title: 요구사항 제목 (간결하게)
- description: 요구사항 상세 설명
- keywords: 관련 키워드 리스트

문서 내용:
```
{text[:5000]}  # 처음 5000자만
```

JSON 형식으로만 응답해주세요:
{{
  "requirements": [
    {{
      "id": "REQ-001",
      "type": "technical",
      "priority": "mandatory",
      "title": "...",
      "description": "...",
      "keywords": ["..."]
    }}
  ]
}}
"""
        
        return prompt
    
    async def _call_llm(self, prompt: str) -> str:
        """LLM을 호출합니다."""
        # 실제 구현에서는 Gemini API 호출
        # 예시:
        # response = await self.llm_client.generate_content(prompt)
        # return response.text
        
        # 임시 구현
        return '{"requirements": []}'
    
    def _parse_llm_response(self, response: str) -> List[Requirement]:
        """LLM 응답을 파싱합니다."""
        try:
            data = json.loads(response)
            requirements = []
            
            for req_data in data.get("requirements", []):
                requirement = Requirement(
                    id=req_data["id"],
                    type=RequirementType(req_data["type"]),
                    priority=RequirementPriority(req_data["priority"]),
                    title=req_data["title"],
                    description=req_data["description"],
                    keywords=req_data.get("keywords", []),
                )
                requirements.append(requirement)
            
            return requirements
            
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            print(f"LLM 응답 파싱 실패: {e}")
            return []
    
    def extract_requirements_from_section(
        self, 
        section_text: str,
        section_name: str,
        page_number: Optional[int] = None
    ) -> List[Requirement]:
        """특정 섹션에서 요구사항을 추출합니다 (동기 버전).
        
        Args:
            section_text: 섹션 텍스트
            section_name: 섹션 이름
            page_number: 페이지 번호
            
        Returns:
            추출된 요구사항 리스트
        """
        # 간단한 패턴 기반 추출 (LLM 없이)
        requirements = []
        
        # 섹션을 문장으로 분리
        sentences = self._split_into_sentences(section_text)
        
        for idx, sentence in enumerate(sentences, start=1):
            # 요구사항처럼 보이는 문장 필터링
            if self._is_requirement_sentence(sentence):
                req_id = f"REQ-{page_number or 0:03d}-{idx:02d}"
                
                requirement = Requirement(
                    id=req_id,
                    type=self._infer_type(sentence),
                    priority=self._infer_priority(sentence),
                    title=self._create_title(sentence),
                    description=sentence,
                    section=section_name,
                    page_number=page_number,
                    keywords=self._extract_simple_keywords(sentence),
                )
                
                requirements.append(requirement)
        
        return requirements
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """텍스트를 문장으로 분리합니다."""
        import re
        sentences = re.split(r'[.!?]\s+', text)
        return [s.strip() for s in sentences if len(s.strip()) > 20]
    
    def _is_requirement_sentence(self, sentence: str) -> bool:
        """요구사항 문장인지 판단합니다."""
        keywords = [
            "해야", "필요", "요구", "제공", "포함", "구현",
            "must", "shall", "should", "required", "need"
        ]
        return any(keyword in sentence.lower() for keyword in keywords)
    
    def _infer_type(self, text: str) -> RequirementType:
        """타입을 추론합니다."""
        text_lower = text.lower()
        
        if any(k in text_lower for k in ["기술", "technical", "시스템", "아키텍처"]):
            return RequirementType.TECHNICAL
        elif any(k in text_lower for k in ["기능", "functional"]):
            return RequirementType.FUNCTIONAL
        elif any(k in text_lower for k in ["조직", "팀", "organizational"]):
            return RequirementType.ORGANIZATIONAL
        elif any(k in text_lower for k in ["재무", "예산", "financial"]):
            return RequirementType.FINANCIAL
        elif any(k in text_lower for k in ["법", "규정", "legal"]):
            return RequirementType.LEGAL
        else:
            return RequirementType.OTHER
    
    def _infer_priority(self, text: str) -> RequirementPriority:
        """우선순위를 추론합니다."""
        text_lower = text.lower()
        
        if any(k in text_lower for k in ["필수", "mandatory", "must", "required"]):
            return RequirementPriority.MANDATORY
        elif any(k in text_lower for k in ["강력", "highly"]):
            return RequirementPriority.HIGHLY_DESIRABLE
        elif any(k in text_lower for k in ["권장", "should", "recommended"]):
            return RequirementPriority.DESIRABLE
        else:
            return RequirementPriority.OPTIONAL
    
    def _create_title(self, sentence: str) -> str:
        """문장에서 제목을 생성합니다."""
        # 첫 50자
        title = sentence[:50]
        if len(sentence) > 50:
            title += "..."
        return title
    
    def _extract_simple_keywords(self, text: str) -> List[str]:
        """간단한 키워드를 추출합니다."""
        import re
        
        # 2~15자의 한글/영문 단어
        words = re.findall(r'\b[가-힣]{2,15}\b|\b[A-Za-z]{2,15}\b', text)
        
        # 불용어 제거
        stopwords = {"이", "그", "저", "것", "수", "등", "및", "the", "is", "are", "and", "or"}
        keywords = [w for w in words if w.lower() not in stopwords]
        
        # 중복 제거 및 최대 5개
        return list(set(keywords))[:5]
