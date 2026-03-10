"""RfP 저장소.

RfP 문서와 요구사항을 저장하고 조회합니다.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime

from app.domain.rfp.schemas.rfp_schema import (
    RfPDocument,
    Requirement,
    RequirementType,
    RequirementPriority,
)


class RequirementRepository:
    """요구사항 저장소."""
    
    def __init__(self, storage_path: Optional[Path] = None):
        """
        Args:
            storage_path: 저장 경로 (기본: data/rfp/requirements/)
        """
        self.storage_path = storage_path or Path("data/rfp/requirements")
        self.storage_path.mkdir(parents=True, exist_ok=True)
    
    def save_requirement(self, requirement: Requirement, rfp_id: str) -> None:
        """요구사항을 저장합니다.
        
        Args:
            requirement: 저장할 요구사항
            rfp_id: RfP ID
        """
        file_path = self.storage_path / f"{rfp_id}_requirements.jsonl"
        
        # JSONL 형식으로 추가
        with open(file_path, "a", encoding="utf-8") as f:
            json.dump(requirement.model_dump(), f, ensure_ascii=False)
            f.write("\n")
    
    def save_requirements(
        self, 
        requirements: List[Requirement], 
        rfp_id: str,
        overwrite: bool = False
    ) -> None:
        """여러 요구사항을 저장합니다.
        
        Args:
            requirements: 저장할 요구사항 리스트
            rfp_id: RfP ID
            overwrite: True면 기존 파일 덮어쓰기
        """
        file_path = self.storage_path / f"{rfp_id}_requirements.jsonl"
        
        mode = "w" if overwrite else "a"
        
        with open(file_path, mode, encoding="utf-8") as f:
            for requirement in requirements:
                json.dump(requirement.model_dump(), f, ensure_ascii=False)
                f.write("\n")
    
    def load_requirements(self, rfp_id: str) -> List[Requirement]:
        """RfP의 모든 요구사항을 로드합니다.
        
        Args:
            rfp_id: RfP ID
            
        Returns:
            요구사항 리스트
        """
        file_path = self.storage_path / f"{rfp_id}_requirements.jsonl"
        
        if not file_path.exists():
            return []
        
        requirements = []
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    data = json.loads(line)
                    requirements.append(Requirement(**data))
        
        return requirements
    
    def find_requirements_by_type(
        self, 
        rfp_id: str, 
        req_type: RequirementType
    ) -> List[Requirement]:
        """특정 타입의 요구사항을 찾습니다.
        
        Args:
            rfp_id: RfP ID
            req_type: 요구사항 타입
            
        Returns:
            필터링된 요구사항 리스트
        """
        all_requirements = self.load_requirements(rfp_id)
        return [r for r in all_requirements if r.type == req_type]
    
    def find_requirements_by_priority(
        self, 
        rfp_id: str, 
        priority: RequirementPriority
    ) -> List[Requirement]:
        """특정 우선순위의 요구사항을 찾습니다.
        
        Args:
            rfp_id: RfP ID
            priority: 우선순위
            
        Returns:
            필터링된 요구사항 리스트
        """
        all_requirements = self.load_requirements(rfp_id)
        return [r for r in all_requirements if r.priority == priority]
    
    def search_requirements(
        self, 
        rfp_id: str, 
        keyword: str
    ) -> List[Requirement]:
        """키워드로 요구사항을 검색합니다.
        
        Args:
            rfp_id: RfP ID
            keyword: 검색 키워드
            
        Returns:
            검색된 요구사항 리스트
        """
        all_requirements = self.load_requirements(rfp_id)
        keyword_lower = keyword.lower()
        
        results = []
        for req in all_requirements:
            if (keyword_lower in req.title.lower() or 
                keyword_lower in req.description.lower() or
                any(keyword_lower in k.lower() for k in req.keywords)):
                results.append(req)
        
        return results
    
    def get_requirement_by_id(
        self, 
        rfp_id: str, 
        req_id: str
    ) -> Optional[Requirement]:
        """ID로 요구사항을 조회합니다.
        
        Args:
            rfp_id: RfP ID
            req_id: 요구사항 ID
            
        Returns:
            요구사항 또는 None
        """
        all_requirements = self.load_requirements(rfp_id)
        for req in all_requirements:
            if req.id == req_id:
                return req
        return None
    
    def delete_requirements(self, rfp_id: str) -> None:
        """RfP의 모든 요구사항을 삭제합니다.
        
        Args:
            rfp_id: RfP ID
        """
        file_path = self.storage_path / f"{rfp_id}_requirements.jsonl"
        if file_path.exists():
            file_path.unlink()
    
    def get_statistics(self, rfp_id: str) -> Dict[str, Any]:
        """요구사항 통계를 반환합니다.
        
        Args:
            rfp_id: RfP ID
            
        Returns:
            통계 딕셔너리
        """
        requirements = self.load_requirements(rfp_id)
        
        if not requirements:
            return {
                "total": 0,
                "by_type": {},
                "by_priority": {},
            }
        
        stats = {
            "total": len(requirements),
            "by_type": {},
            "by_priority": {},
        }
        
        # 타입별 통계
        for req_type in RequirementType:
            count = sum(1 for r in requirements if r.type == req_type)
            if count > 0:
                stats["by_type"][req_type.value] = count
        
        # 우선순위별 통계
        for priority in RequirementPriority:
            count = sum(1 for r in requirements if r.priority == priority)
            if count > 0:
                stats["by_priority"][priority.value] = count
        
        return stats


class RfPDocumentRepository:
    """RfP 문서 저장소."""
    
    def __init__(self, storage_path: Optional[Path] = None):
        """
        Args:
            storage_path: 저장 경로 (기본: data/rfp/documents/)
        """
        self.storage_path = storage_path or Path("data/rfp/documents")
        self.storage_path.mkdir(parents=True, exist_ok=True)
    
    def save_document(self, document: RfPDocument) -> None:
        """RfP 문서를 저장합니다.
        
        Args:
            document: 저장할 RfP 문서
        """
        rfp_id = document.metadata.rfp_id
        file_path = self.storage_path / f"{rfp_id}.json"
        
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(document.model_dump(), f, ensure_ascii=False, indent=2)
    
    def load_document(self, rfp_id: str) -> Optional[RfPDocument]:
        """RfP 문서를 로드합니다.
        
        Args:
            rfp_id: RfP ID
            
        Returns:
            RfP 문서 또는 None
        """
        file_path = self.storage_path / f"{rfp_id}.json"
        
        if not file_path.exists():
            return None
        
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return RfPDocument(**data)
    
    def list_documents(self) -> List[str]:
        """저장된 모든 RfP ID를 반환합니다.
        
        Returns:
            RfP ID 리스트
        """
        return [f.stem for f in self.storage_path.glob("*.json")]
    
    def delete_document(self, rfp_id: str) -> None:
        """RfP 문서를 삭제합니다.
        
        Args:
            rfp_id: RfP ID
        """
        file_path = self.storage_path / f"{rfp_id}.json"
        if file_path.exists():
            file_path.unlink()
