# KOICA 프로젝트 DDD + MCP + Star 토폴로지 전략

## 🎯 프로젝트 목표

**KOICA 사업 입찰 자동화 시스템**
- KoELECTRA: 제출 문서 검증 (누락, 서명, 직인)
- EXAONE: 사업제안서 초안 작성, 용어 검증, LLM 챗봇

---

## 🏗️ Star 토폴로지 아키텍처

### 개념: 중앙 허브 + 전문 에이전트

```
                    ┌─────────────────────┐
                    │   Central Hub       │
                    │  (LangGraph Core)   │
                    │   EXAONE 기반       │
                    └──────────┬──────────┘
                               │
         ┌─────────────────────┼─────────────────────┐
         │                     │                     │
    ┌────▼────┐          ┌────▼────┐          ┌────▼────┐
    │ Agent 1 │          │ Agent 2 │          │ Agent 3 │
    │Document │          │Signature│          │Proposal │
    │Verifier │          │Verifier │          │Writer   │
    │KoELECTRA│          │KoELECTRA│          │EXAONE   │
    └─────────┘          └─────────┘          └─────────┘
         │                     │                     │
         └─────────────────────┼─────────────────────┘
                               │
                    ┌──────────▼──────────┐
                    │   MCP Tool Layer    │
                    │  (Tool Registry)    │
                    └─────────────────────┘
```

**핵심 원리**:
- **Central Hub**: EXAONE 기반 중앙 오케스트레이터 (의사결정)
- **Specialized Agents**: 각 전문 작업 수행 (KoELECTRA, EXAONE)
- **MCP Tools**: 표준화된 도구 인터페이스
- **Star Topology**: Hub가 모든 Agent를 조율

---

## 📐 DDD 도메인 설계

### 단일 도메인: KOICA

```
app/domain/koica/
├── models/                         # 도메인 모델
│   ├── bid.py                      # 입찰 정보
│   ├── document.py                 # 제출 문서
│   ├── proposal.py                 # 사업제안서
│   └── verification.py             # 검증 결과
│
├── agents/                         # MCP 에이전트 (Star 포인트)
│   ├── document_verifier.py        # KoELECTRA - 문서 누락 검증
│   ├── signature_verifier.py       # KoELECTRA - 서명/직인 검증
│   ├── proposal_writer.py          # EXAONE - 제안서 초안 작성
│   ├── terminology_checker.py      # EXAONE - 용어 일탈 검증
│   └── chat_assistant.py           # EXAONE - LLM 챗봇
│
├── orchestrators/                  # LangGraph 중앙 허브
│   ├── bid_hub.py                  # ⭐ Star 중심 (EXAONE)
│   ├── verification_workflow.py    # 검증 워크플로우
│   └── proposal_workflow.py        # 제안서 작성 워크플로우
│
├── mcp/                            # MCP 레이어
│   ├── tools/                      # MCP Tool 정의
│   │   ├── document_tool.py
│   │   ├── signature_tool.py
│   │   ├── proposal_tool.py
│   │   ├── terminology_tool.py
│   │   └── chat_tool.py
│   │
│   ├── registry.py                 # Tool Registry
│   └── protocol.py                 # MCP Protocol 구현
│
├── services/                       # 비즈니스 로직
│   ├── document_service.py
│   ├── proposal_service.py
│   └── verification_service.py
│
├── repositories/                   # 데이터 접근
│   ├── bid_repository.py
│   ├── document_repository.py
│   └── proposal_repository.py
│
└── router.py                       # KOICA API
```

---

## 🌟 Star 토폴로지 상세 설계

### 1. Central Hub (중앙 허브)

**파일**: `app/domain/koica/orchestrators/bid_hub.py`

**역할**:
- 사용자 요청 분석 (EXAONE)
- 적절한 Agent 선택 및 호출
- Agent 결과 통합 및 최종 응답 생성
- 워크플로우 조율

**구현**:
```python
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage

class BidHub:
    """KOICA 입찰 중앙 허브 (Star 중심)"""
    
    def __init__(self, exaone_model, mcp_registry):
        self.exaone = exaone_model  # 중앙 의사결정 모델
        self.registry = mcp_registry  # MCP Tool Registry
        self.graph = self._build_graph()
    
    def _build_graph(self):
        """Star 토폴로지 그래프 구축"""
        workflow = StateGraph(BidState)
        
        # 중앙 노드
        workflow.add_node("hub", self.hub_node)
        
        # Agent 노드들 (Star 포인트)
        workflow.add_node("document_verifier", self.document_agent)
        workflow.add_node("signature_verifier", self.signature_agent)
        workflow.add_node("proposal_writer", self.proposal_agent)
        workflow.add_node("terminology_checker", self.terminology_agent)
        workflow.add_node("chat_assistant", self.chat_agent)
        
        # Star 구조: Hub → Agents → Hub
        workflow.set_entry_point("hub")
        workflow.add_conditional_edges(
            "hub",
            self.route_to_agent,  # Hub가 Agent 선택
            {
                "document": "document_verifier",
                "signature": "signature_verifier",
                "proposal": "proposal_writer",
                "terminology": "terminology_checker",
                "chat": "chat_assistant",
                "end": END
            }
        )
        
        # 모든 Agent는 Hub로 복귀
        for agent in ["document_verifier", "signature_verifier", 
                      "proposal_writer", "terminology_checker", "chat_assistant"]:
            workflow.add_edge(agent, "hub")
        
        return workflow.compile()
    
    def hub_node(self, state: BidState):
        """중앙 허브 노드 (EXAONE 기반 의사결정)"""
        # EXAONE으로 사용자 의도 파악
        intent = self.exaone.analyze_intent(state["messages"][-1])
        
        # Agent 결과가 있으면 통합
        if state.get("agent_results"):
            final_response = self.exaone.synthesize_results(
                state["agent_results"]
            )
            state["messages"].append(AIMessage(content=final_response))
            state["next_action"] = "end"
        else:
            # 다음 Agent 결정
            state["next_action"] = intent["agent"]
        
        return state
    
    def route_to_agent(self, state: BidState) -> str:
        """Hub에서 Agent로 라우팅"""
        return state["next_action"]
```

---

### 2. Specialized Agents (전문 에이전트)

#### Agent 1: Document Verifier (KoELECTRA)

**파일**: `app/domain/koica/agents/document_verifier.py`

**역할**: 제출 문서 누락 검증

```python
from artifacts.models.implementations.koelectra import KoElectraLLM

class DocumentVerifierAgent:
    """문서 누락 검증 에이전트 (KoELECTRA)"""
    
    def __init__(self, koelectra_model):
        self.model = koelectra_model
        self.required_docs = [
            "사업제안서", "사업예산서", "사업수행계획서",
            "기술제안서", "인력운용계획서", "법인등록증"
        ]
    
    def verify(self, documents: list[str]) -> dict:
        """문서 누락 검증"""
        results = []
        for required in self.required_docs:
            # KoELECTRA로 문서 존재 여부 분류
            exists = self.model.classify(
                text=f"제출 문서 목록: {', '.join(documents)}",
                query=f"{required} 포함 여부"
            )
            results.append({
                "document": required,
                "exists": exists["label"] == "present",
                "confidence": exists["score"]
            })
        
        return {
            "missing_docs": [r["document"] for r in results if not r["exists"]],
            "verified_docs": [r["document"] for r in results if r["exists"]],
            "details": results
        }
```

#### Agent 2: Signature Verifier (KoELECTRA)

**파일**: `app/domain/koica/agents/signature_verifier.py`

**역할**: 서명/직인 누락 검증

```python
class SignatureVerifierAgent:
    """서명/직인 검증 에이전트 (KoELECTRA)"""
    
    def __init__(self, koelectra_model):
        self.model = koelectra_model
        self.required_signatures = [
            "대표자 서명", "사업책임자 서명", "법인 직인"
        ]
    
    def verify(self, document_images: list) -> dict:
        """서명/직인 검증"""
        # OCR + KoELECTRA 분류
        results = []
        for sig_type in self.required_signatures:
            detected = self.model.classify(
                text=self._extract_text_from_images(document_images),
                query=f"{sig_type} 존재 여부"
            )
            results.append({
                "signature_type": sig_type,
                "detected": detected["label"] == "present",
                "confidence": detected["score"]
            })
        
        return {
            "missing_signatures": [r["signature_type"] for r in results if not r["detected"]],
            "verified_signatures": [r["signature_type"] for r in results if r["detected"]],
            "details": results
        }
```

#### Agent 3: Proposal Writer (EXAONE)

**파일**: `app/domain/koica/agents/proposal_writer.py`

**역할**: 사업제안서 초안 작성

```python
class ProposalWriterAgent:
    """제안서 작성 에이전트 (EXAONE)"""
    
    def __init__(self, exaone_model):
        self.model = exaone_model
    
    def generate_draft(self, bid_info: dict) -> str:
        """제안서 초안 생성"""
        prompt = f"""
        KOICA 사업제안서를 작성해주세요.
        
        사업명: {bid_info['project_name']}
        대상국가: {bid_info['target_country']}
        사업분야: {bid_info['sector']}
        예산: {bid_info['budget']}
        
        다음 구조로 작성:
        1. 사업 배경 및 필요성
        2. 사업 목표 및 기대효과
        3. 사업 추진 전략
        4. 예산 계획
        5. 위험 관리 방안
        """
        
        draft = self.model.generate(prompt)
        return draft
```

#### Agent 4: Terminology Checker (EXAONE)

**파일**: `app/domain/koica/agents/terminology_checker.py`

**역할**: 한국어 용어 일탈 검증

```python
class TerminologyCheckerAgent:
    """용어 일탈 검증 에이전트 (EXAONE)"""
    
    def __init__(self, exaone_model, terminology_db):
        self.model = exaone_model
        self.terminology_db = terminology_db  # KOICA 용어사전
    
    def check(self, text: str) -> dict:
        """용어 일탈 검증"""
        # EXAONE으로 용어 추출 및 검증
        prompt = f"""
        다음 텍스트에서 KOICA 표준 용어와 다른 표현을 찾아주세요.
        
        텍스트: {text}
        
        표준 용어사전: {self.terminology_db}
        """
        
        issues = self.model.analyze(prompt)
        return {
            "deviations": issues["non_standard_terms"],
            "suggestions": issues["standard_alternatives"],
            "severity": issues["severity_level"]
        }
```

#### Agent 5: Chat Assistant (EXAONE)

**파일**: `app/domain/koica/agents/chat_assistant.py`

**역할**: LLM 챗봇 (일반 질의응답)

```python
class ChatAssistantAgent:
    """챗봇 에이전트 (EXAONE)"""
    
    def __init__(self, exaone_model, rag_service):
        self.model = exaone_model
        self.rag = rag_service
    
    def chat(self, message: str) -> str:
        """일반 챗봇 응답"""
        # RAG로 관련 문서 검색
        context = self.rag.search(message)
        
        # EXAONE으로 응답 생성
        response = self.model.generate(
            prompt=f"질문: {message}\n\n참고 자료: {context}"
        )
        return response
```

---

### 3. MCP Tool Layer

**파일**: `app/domain/koica/mcp/registry.py`

**역할**: Agent를 MCP Tool로 등록 및 관리

```python
from typing import Dict, Callable

class MCPToolRegistry:
    """MCP Tool Registry (Star 토폴로지 관리)"""
    
    def __init__(self):
        self.tools: Dict[str, Callable] = {}
    
    def register(self, name: str, agent: Callable, description: str):
        """Agent를 MCP Tool로 등록"""
        self.tools[name] = {
            "function": agent,
            "description": description,
            "type": "mcp_tool"
        }
    
    def get_tool(self, name: str):
        """Tool 조회"""
        return self.tools.get(name)
    
    def list_tools(self):
        """사용 가능한 Tool 목록"""
        return [
            {"name": name, "description": tool["description"]}
            for name, tool in self.tools.items()
        ]

# 사용 예시
registry = MCPToolRegistry()

# Agent를 MCP Tool로 등록
registry.register(
    name="verify_documents",
    agent=document_verifier.verify,
    description="제출 문서 누락 검증"
)

registry.register(
    name="verify_signatures",
    agent=signature_verifier.verify,
    description="서명/직인 누락 검증"
)

registry.register(
    name="write_proposal",
    agent=proposal_writer.generate_draft,
    description="사업제안서 초안 작성"
)

registry.register(
    name="check_terminology",
    agent=terminology_checker.check,
    description="용어 일탈 검증"
)

registry.register(
    name="chat",
    agent=chat_assistant.chat,
    description="일반 질의응답"
)
```

---

## 🔄 워크플로우 예시

### 시나리오 1: 입찰 서류 검증

```
사용자: "입찰 서류를 검증해주세요"
    ↓
[Hub] EXAONE 의도 분석 → "문서 검증 + 서명 검증 필요"
    ↓
[Hub → Document Verifier] KoELECTRA 문서 누락 검증
    ↓
[Document Verifier → Hub] 결과 반환: "사업예산서 누락"
    ↓
[Hub → Signature Verifier] KoELECTRA 서명/직인 검증
    ↓
[Signature Verifier → Hub] 결과 반환: "법인 직인 누락"
    ↓
[Hub] EXAONE 결과 통합 및 최종 응답 생성
    ↓
사용자: "사업예산서와 법인 직인이 누락되었습니다. 제출 전 확인 바랍니다."
```

### 시나리오 2: 제안서 작성 + 용어 검증

```
사용자: "탄자니아 보건사업 제안서를 작성해주세요"
    ↓
[Hub] EXAONE 의도 분석 → "제안서 작성 필요"
    ↓
[Hub → Proposal Writer] EXAONE 제안서 초안 생성
    ↓
[Proposal Writer → Hub] 초안 반환
    ↓
[Hub] EXAONE 판단 → "용어 검증 필요"
    ↓
[Hub → Terminology Checker] EXAONE 용어 일탈 검증
    ↓
[Terminology Checker → Hub] 결과 반환: "수혜자 → 사업대상자"
    ↓
[Hub] EXAONE 최종 제안서 생성 (용어 수정 반영)
    ↓
사용자: "제안서 초안이 완성되었습니다. (용어 2건 수정됨)"
```

---

## 📊 최종 프로젝트 구조

```
프로젝트 루트/
├── app/
│   ├── domain/
│   │   └── koica/                      ⭐ 단일 핵심 도메인
│   │       ├── models/                 # 도메인 모델
│   │       │   ├── bid.py
│   │       │   ├── document.py
│   │       │   ├── proposal.py
│   │       │   └── verification.py
│   │       │
│   │       ├── agents/                 # MCP 에이전트 (Star 포인트)
│   │       │   ├── document_verifier.py    # KoELECTRA
│   │       │   ├── signature_verifier.py   # KoELECTRA
│   │       │   ├── proposal_writer.py      # EXAONE
│   │       │   ├── terminology_checker.py  # EXAONE
│   │       │   └── chat_assistant.py       # EXAONE
│   │       │
│   │       ├── orchestrators/          # LangGraph 중앙 허브
│   │       │   ├── bid_hub.py              # ⭐ Star 중심
│   │       │   ├── verification_workflow.py
│   │       │   └── proposal_workflow.py
│   │       │
│   │       ├── mcp/                    # MCP 레이어
│   │       │   ├── tools/
│   │       │   ├── registry.py
│   │       │   └── protocol.py
│   │       │
│   │       ├── services/               # 비즈니스 로직
│   │       ├── repositories/           # 데이터 접근
│   │       └── router.py               # KOICA API
│   │
│   ├── core/                           # 인프라
│   │   ├── database.py
│   │   ├── embeddings.py
│   │   └── vectorstore.py
│   │
│   ├── main.py
│   └── schemas.py
│
├── artifacts/                          # 모델 코드
│   └── models/
│       ├── interfaces/
│       │   └── base.py
│       ├── implementations/
│       │   ├── exaone/
│       │   │   └── exaone.py
│       │   └── koelectra/              ⭐ 추가
│       │       └── koelectra.py
│       └── core/
│           └── manager.py
│
├── models/                             # 모델 파일 (데이터)
│   ├── exaone-2.4b/
│   └── koelectra-small-v3-discriminator/
│
├── data/
│   └── koica_data/                     # KOICA 훈련 데이터
│
└── config.py
```

---

## 🎯 핵심 설계 원칙

### 1. Star 토폴로지
- **중앙 허브**: EXAONE 기반 `BidHub` (의사결정)
- **전문 Agent**: KoELECTRA (검증), EXAONE (생성/분석)
- **양방향 통신**: Hub ↔ Agent

### 2. MCP 프로토콜
- **Tool Registry**: Agent를 표준화된 Tool로 등록
- **Protocol**: 일관된 입출력 인터페이스
- **확장성**: 새 Agent 추가 용이

### 3. DDD 도메인
- **단일 도메인**: KOICA (입찰 자동화)
- **명확한 경계**: 모델, 에이전트, 오케스트레이터 분리
- **비즈니스 중심**: 입찰 프로세스 중심 설계

---

## 🚀 구현 우선순위

### Phase 1: 기초 인프라 (Week 1-2)
1. ✅ KoELECTRA 모델 다운로드 (완료)
2. ✅ EXAONE 모델 로더 (완료)
3. [ ] `artifacts/models/implementations/koelectra/` 구현
4. [ ] MCP Tool Registry 구현
5. [ ] KOICA 도메인 모델 정의

### Phase 2: Agent 구현 (Week 3-4)
1. [ ] Document Verifier (KoELECTRA)
2. [ ] Signature Verifier (KoELECTRA)
3. [ ] Proposal Writer (EXAONE)
4. [ ] Terminology Checker (EXAONE)
5. [ ] Chat Assistant (EXAONE)

### Phase 3: Central Hub (Week 5-6)
1. [ ] BidHub 구현 (LangGraph)
2. [ ] Star 토폴로지 워크플로우
3. [ ] Agent 라우팅 로직
4. [ ] 결과 통합 로직

### Phase 4: 통합 및 테스트 (Week 7-8)
1. [ ] KOICA API 엔드포인트
2. [ ] 전체 워크플로우 테스트
3. [ ] 프론트엔드 통합
4. [ ] 성능 최적화

---

## 📈 예상 효과

### 기술적 효과
- ✅ 모듈화된 Agent 구조
- ✅ 확장 가능한 MCP 아키텍처
- ✅ 명확한 책임 분리 (DDD)
- ✅ 유지보수 용이성

### 비즈니스 효과
- ✅ 입찰 서류 검증 자동화 (시간 90% 단축)
- ✅ 제안서 초안 자동 생성 (품질 향상)
- ✅ 용어 일관성 보장 (오류 감소)
- ✅ 24/7 챗봇 지원

---

**작성일**: 2026-01-19
**버전**: 2.0 (KOICA 특화)
**다음 단계**: KoELECTRA 모델 래퍼 구현 → MCP Registry 구현 → BidHub 구현
