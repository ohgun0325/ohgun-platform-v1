# KOICA 프로젝트 백엔드 주요 구성 기술

## 목차
1. [프로젝트 개요](#1-프로젝트-개요)
2. [데이터베이스 구조](#2-데이터베이스-구조)
3. [AI 에이전트 시스템](#3-ai-에이전트-시스템)
4. [LangGraph 기반 RAG 파이프라인](#4-langgraph-기반-rag-파이프라인)
5. [스타 토폴로지 구조](#5-스타-토폴로지-구조)
6. [문서 처리 기술](#6-문서-처리-기술)
7. [머신러닝 모델](#7-머신러닝-모델)
8. [MCP(Model Context Protocol) 서버](#8-mcpmodel-context-protocol-서버)

---

## 1. 프로젝트 개요

### 1.1 기술 스택 요약

| 구성 요소 | 기술 | 버전 | 역할 |
|-----------|------|------|------|
| **백엔드 프레임워크** | FastAPI | 0.104.0+ | RESTful API 서버 |
| **데이터베이스** | PostgreSQL (NeonDB) | - | 관계형 데이터베이스 |
| **벡터 검색** | pgvector | 0.2.4+ | 임베딩 벡터 저장 및 유사도 검색 |
| **ORM & 마이그레이션** | Alembic | - | 데이터베이스 스키마 관리 |
| **LLM 프레임워크** | LangChain | 0.1.0+ | LLM 애플리케이션 개발 |
| **워크플로우 엔진** | LangGraph | 0.2.0+ | 에이전트 워크플로우 구성 |
| **로컬 LLM** | Exaone 3.5 (2.4B) | - | 온프레미스 언어 모델 |
| **임베딩 모델** | jhgan/ko-sroberta-multitask | - | 한국어 임베딩 (768차원) |
| **PDF 파싱** | PyMuPDF, PDFplumber | 1.23.0+, 0.11.0+ | PDF 텍스트/이미지 추출 |
| **객체 검출** | YOLO (Ultralytics) | 8.0.0+ | 인감도장/서명 검출 |
| **분류 모델** | KoELECTRA | - | 정책/규칙 분류 |

### 1.2 프로젝트 구조

```
langchain/
├── app/
│   ├── domain/
│   │   ├── koica/              # KOICA 도메인 (메인 Star)
│   │   │   ├── hub/
│   │   │   │   └── orchestrators/
│   │   │   │       ├── koica_orchestrator.py    # KOICA 메인 오케스트레이터
│   │   │   │       ├── term_orchestrator.py      # ODA 용어사전
│   │   │   │       └── general_orchestrator.py   # 일반 질의 처리
│   │   │   ├── mcp/                              # MCP 서버
│   │   │   │   ├── server.py                     # KoicaMCPServer
│   │   │   │   └── tools.py                      # MCP Tools (KoElectra, Exaone, FileSystem)
│   │   │   └── services/
│   │   │       ├── koica_test_qa_service.py      # Q&A 매칭
│   │   │       └── policy_rule_classifier.py     # KoELECTRA 분류기
│   │   ├── soccer/             # Soccer 도메인 (독립 Star)
│   │   │   └── hub/
│   │   │       └── orchestrators/
│   │   │           └── soccer_orchestrator.py
│   │   ├── chat/               # 통합 채팅 계층
│   │   │   ├── orchestrators/
│   │   │   │   └── chat_orchestrator.py          # 최상위 라우터
│   │   │   └── services/
│   │   │       └── question_classifier.py        # 도메인 분류기
│   │   └── terms/              # ODA 용어사전 (Koica Star 내부)
│   │       └── services/
│   │           └── term_service.py
│   ├── api/
│   │   └── v1/
│   │       ├── koica/          # KOICA API 엔드포인트
│   │       └── v10/
│   │           └── soccer/     # Soccer API 엔드포인트
│   ├── core/
│   │   ├── config.py           # 설정 관리
│   │   ├── embeddings.py       # 임베딩 생성
│   │   └── vectorstore.py      # 벡터 검색
│   ├── graph.py                # LangGraph RAG 파이프라인
│   └── alembic/                # DB 마이그레이션
├── data/
│   └── koica_data/             # KOICA 데이터셋
└── artifacts/
    └── models/                 # 로컬 모델 저장소
```

---

## 2. 데이터베이스 구조

### 2.1 PostgreSQL + pgvector

**NeonDB**를 사용하며, **pgvector** 확장을 통해 벡터 유사도 검색을 지원합니다.

### 2.2 주요 테이블

#### 2.2.1 임베딩 테이블 (players_embeddings 예시)

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE players_embeddings (
    id BIGSERIAL PRIMARY KEY,
    player_id VARCHAR(20) NOT NULL REFERENCES player(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    embedding vector(768) NOT NULL,  -- jhgan/ko-sroberta-multitask 임베딩
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

CREATE INDEX ix_players_embeddings_player_id ON players_embeddings (player_id);
```

#### 2.2.2 벡터 유사도 검색 쿼리

```python
# 코사인 유사도 기반 검색
query = """
    SELECT content, 1 - (embedding <=> %s::vector) AS similarity
    FROM players_embeddings
    ORDER BY embedding <=> %s::vector
    LIMIT %s
"""
cursor.execute(query, (query_vector, query_vector, limit))
```

### 2.3 마이그레이션 관리 (Alembic)

```bash
# 마이그레이션 생성
alembic revision --autogenerate -m "create players_embeddings table"

# 마이그레이션 적용
alembic upgrade head

# 롤백
alembic downgrade -1
```

**마이그레이션 파일 예시**: `app/alembic/versions/20260202_1500_players_embeddings_table.py`

---

## 3. AI 에이전트 시스템

### 3.1 오케스트레이터 패턴

각 도메인은 **Orchestrator**를 통해 질의를 처리하며, 계층적으로 구성됩니다.

```
ChatOrchestrator (최상위)
    ├── QuestionClassifier (도메인 분류)
    │
    ├── KoicaOrchestrator (KOICA 도메인)
    │   ├── KoicaTestQAService (Q&A 매칭)
    │   ├── PolicyRuleClassifier (KoELECTRA)
    │   ├── KoicaMCPServer (MCP 파이프라인)
    │   ├── TermService (ODA 용어사전)
    │   └── GeneralOrchestrator (Fallback)
    │
    └── SoccerOrchestrator (Soccer 도메인)
        └── (독립 처리)
```

### 3.2 ChatOrchestrator (최상위 라우터)

```python
class ChatOrchestrator:
    """전체 챗봇 흐름을 조율하는 오케스트레이터."""

    def __init__(self):
        self._classifier = QuestionClassifier()  # 도메인 분류기
        self._koica_orch = KoicaOrchestrator()
        self._soccer_orch = SoccerOrchestrator()

    async def route_question(self, question: str, context: Dict[str, Any]) -> ChatResult:
        """질문을 분류하고 적절한 도메인 오케스트레이터로 전달"""
        classification = self._classifier.classify(question)
        
        if classification.domain == "soccer":
            return await self._soccer_orch.process(question, context)
        else:  # koica, term, general
            return await self._koica_orch.process(question, context)
```

### 3.3 KoicaOrchestrator (KOICA 도메인)

```python
class KoicaOrchestrator:
    """KOICA 도메인 질의를 처리하는 오케스트레이터."""
    
    async def process(self, question: str, context: Dict[str, Any]) -> ChatResult:
        """
        1) ODA 용어사전 검색 (domain=="term")
        2) KOICA Q&A 데이터셋 매칭
        3) MCP 파이프라인 (KoElectra → Exaone)
        4) KOICA RAG (벡터 검색 + Exaone 생성)
        5) GeneralOrchestrator (최종 Fallback)
        """
        
        # 1) ODA 용어사전 우선 검색
        if context.get("domain") == "term":
            entries = self._term_service.search_terms(query=question, limit=3)
            if entries:
                return ChatResult(answer=..., sources=["oda_term_dictionary"])
        
        # 2) KOICA test셋 기반 Q&A 매칭
        hit = self._qa_service.find_best_answer(question)
        if hit is not None:
            return ChatResult(answer=..., sources=["koica_data_test.jsonl"])
        
        # 3) MCP 서버를 통한 KoElectra + Exaone 파이프라인
        if self._mcp_server and self._exaone_model:
            mcp_result = self._mcp_server._classify_and_generate(question=question)
            if mcp_result.get("response"):
                return ChatResult(answer=mcp_result["response"], sources=["mcp_pipeline"])
        
        # 4) KOICA RAG (벡터 검색 + Exaone)
        if db_conn and chat_model:
            response = run_rag_chat(question, chat_model, db_conn, embedding_dim)
            return ChatResult(answer=response, sources=[])
        
        # 5) 최종 fallback
        return await self._general_orch.process(question, context)
```

---

## 4. LangGraph 기반 RAG 파이프라인

### 4.1 LangGraph 개요

**LangGraph**는 LangChain에서 제공하는 **상태 기반 워크플로우 엔진**으로, 복잡한 AI 에이전트 흐름을 그래프로 표현합니다.

### 4.2 RAG 파이프라인 구조

```python
# app/graph.py

class AgentState(TypedDict):
    """LangGraph 상태 정의"""
    messages: Annotated[list, add_messages]  # 대화 누적
    rag_context: Optional[str]               # RAG 검색 결과

def build_rag_graph(chat_model, db_conn, embedding_dim):
    """RAG 기반 LangGraph 빌드"""
    g = StateGraph(AgentState)
    
    # 노드 추가
    g.add_node("rag_search", rag_search_node)  # 벡터 검색
    g.add_node("model", model_node)            # LLM 생성
    
    # 엔트리 포인트
    g.set_entry_point("rag_search")
    
    # 간단한 선형 흐름 (Exaone은 Tool 미지원)
    g.add_edge("rag_search", "model")
    g.add_edge("model", END)
    
    return g.compile()
```

### 4.3 RAG 검색 노드

```python
def rag_search_node(state: AgentState, db_conn, embedding_dim):
    """RAG 검색을 수행하고 컨텍스트를 상태에 추가"""
    # 1. 마지막 사용자 메시지 가져오기
    user_messages = [msg for msg in state["messages"] if isinstance(msg, HumanMessage)]
    query = user_messages[-1].content
    
    # 2. 임베딩 생성
    query_embeddings = generate_embeddings([query], embedding_dim)
    query_vector = query_embeddings[0]
    
    # 3. 벡터 유사도 검색 (pgvector)
    similar_docs = query_similar_documents(db_conn, query_vector, limit=3)
    
    # 4. 컨텍스트 구성
    if similar_docs:
        context = "\n\n".join([content for _, content, _ in similar_docs])
        return {"rag_context": context}
    else:
        return {"rag_context": None}
```

### 4.4 Model 노드 (Exaone)

```python
def model_node(state: AgentState):
    """LLM을 호출하여 응답 생성"""
    rag_context = state.get("rag_context")
    
    # 시스템 프롬프트 구성
    if rag_context:
        system_content = f"""당신은 친절한 AI 어시스턴트입니다. 
아래 정보를 바탕으로 자연스럽게 답변해주세요.

참고 정보:
{rag_context}"""
    else:
        system_content = "당신은 친절한 AI 어시스턴트입니다."
    
    # 메시지 구성 (Exaone 형식)
    messages_list = [{"role": "system", "content": system_content}]
    for msg in state["messages"]:
        if isinstance(msg, HumanMessage):
            messages_list.append({"role": "user", "content": msg.content})
    
    # Exaone 호출
    response_text = chat_model.invoke(messages_list)
    return {"messages": [AIMessage(content=response_text)]}
```

### 4.5 실행 예시

```python
# RAG 채팅 실행
response = run_rag_chat(
    user_text="KOICA의 주요 사업은 무엇인가요?",
    chat_model=exaone_model,
    db_conn=db_conn,
    embedding_dim=768
)
print(response)
```

---

## 5. 스타 토폴로지 구조

### 5.1 아키텍처 개념

KOICA 프로젝트는 **Star Topology (스타 토폴로지)** 구조를 채택합니다.

```
                    ┌─────────────────────┐
                    │  ChatOrchestrator   │
                    │   (중앙 허브)        │
                    └──────────┬──────────┘
                               │
           ┌───────────────────┼───────────────────┐
           │                   │                   │
    ┌──────▼──────┐    ┌──────▼──────┐    ┌──────▼──────┐
    │   KOICA     │    │   Soccer    │    │   Future    │
    │   (Star 1)  │    │   (Star 2)  │    │   Domains   │
    └──────┬──────┘    └─────────────┘    └─────────────┘
           │
           │ (KOICA Star 내부)
           │
    ┌──────┼──────────────────────┐
    │      │                      │
┌───▼───┐ ┌▼────────┐ ┌──────────▼───┐
│ Terms │ │ General │ │     MCP      │
│(ODA)  │ │(Fallback)│ │   Server    │
└───────┘ └─────────┘ └──────────────┘
```

### 5.2 핵심 원칙

1. **중앙 허브 (ChatOrchestrator)**
   - 모든 질의는 `ChatOrchestrator`를 통해 라우팅
   - `QuestionClassifier`로 도메인 분류 (koica, soccer, term, general)

2. **독립 Stars (도메인)**
   - 각 도메인(KOICA, Soccer)은 독립적인 Star로 구성
   - 도메인 간 의존성 없음 (느슨한 결합)

3. **작은 Stars (서브 도메인)**
   - KOICA Star 내부에 Terms(ODA 용어), General(Fallback) 등의 작은 Star 존재
   - MCP Server는 KOICA Star 내부 스포크로 동작

### 5.3 장점

- **확장성**: 새로운 도메인 추가 시 기존 도메인 영향 없음
- **유지보수성**: 도메인별로 독립적인 코드 관리
- **재사용성**: 각 Star는 독립적으로 테스트 및 배포 가능

---

## 6. 문서 처리 기술

### 6.1 PyMuPDF (fitz)

**PyMuPDF**는 PDF 파싱 및 렌더링을 위한 고성능 라이브러리입니다.

#### 6.1.1 주요 기능

```python
import fitz  # PyMuPDF

# PDF 열기
doc = fitz.open(pdf_path)

# 텍스트 추출 (레이아웃 유지)
for page in doc:
    text = page.get_text("text")
    print(text)

# 이미지 추출
for page_num in range(len(doc)):
    page = doc[page_num]
    images = page.get_images(full=True)
    for img_index, img in enumerate(images):
        xref = img[0]
        base_image = doc.extract_image(xref)
        image_bytes = base_image["image"]

# PDF → 이미지 렌더링 (YOLO 입력용)
for page_num in range(len(doc)):
    page = doc[page_num]
    pix = page.get_pixmap(dpi=250)  # 250 DPI 렌더링
    img_array = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
```

#### 6.1.2 사용 사례

- **인감도장/서명 검출**: PDF를 고해상도 이미지로 렌더링 후 YOLO 모델에 입력
- **텍스트 추출**: RfP 요구사항 ID 파싱 (정규식 매칭)
- **제안서 파싱**: 섹션 헤더 기반 분할

### 6.2 PDFplumber

**PDFplumber**는 표(Table) 추출에 강점이 있는 PDF 파싱 라이브러리입니다.

#### 6.2.1 주요 기능

```python
import pdfplumber

# PDF 열기
with pdfplumber.open(pdf_path) as pdf:
    # 텍스트 추출
    for page in pdf.pages:
        text = page.extract_text()
        print(text)
    
    # 표 추출
    for page in pdf.pages:
        tables = page.extract_tables()
        for table in tables:
            # table은 2D 리스트
            for row in table:
                print(row)
```

#### 6.2.2 사용 사례

- **PDM 매트릭스 추출**: RfP 평가 시스템에서 표 형태의 요구사항 파싱
- **구조화된 데이터 추출**: 프로젝트 일정표, 예산표 등

### 6.3 PDF 파싱 전략 비교

| 라이브러리 | 강점 | 약점 | 사용 사례 |
|-----------|------|------|-----------|
| **PyMuPDF** | 빠른 속도, 이미지 렌더링 | 표 추출 약함 | 텍스트 추출, 이미지 렌더링 |
| **PDFplumber** | 표 추출 강력 | 느린 속도 | 표 데이터 추출 |
| **Camelot** | 고급 표 추출 | 설치 복잡 | 복잡한 표 구조 |

**권장 전략**: PyMuPDF + PDFplumber 조합 사용

```python
def parse_proposal_pdf(pdf_bytes: bytes) -> ProposalDocument:
    """제안서 파싱 (하이브리드 전략)"""
    # 1. PyMuPDF로 텍스트 추출
    text = extract_text_with_pymupdf(pdf_bytes)
    sections = parse_sections_from_text(text)
    
    # 2. PDFplumber로 표 추출
    tables = extract_tables_with_pdfplumber(pdf_bytes)
    
    return ProposalDocument(sections=sections, tables=tables)
```

---

## 7. 머신러닝 모델

### 7.1 YOLO (Ultralytics)

**YOLO v8**을 사용한 객체 검출 (인감도장/서명)

#### 7.1.1 모델 구성

```python
from ultralytics import YOLO

# 모델 로드
model = YOLO("models/stamp_detector/best.pt")

# 검출 실행
results = model.predict(
    source=image_array,
    conf=0.05,  # 신뢰도 임계값 (현재 데이터 기준 낮게 설정)
    verbose=False
)

# 결과 처리
for result in results:
    boxes = result.boxes
    for box in boxes:
        class_id = int(box.cls[0])
        confidence = float(box.conf[0])
        x1, y1, x2, y2 = box.xyxy[0].tolist()
        
        print(f"검출: 클래스={class_id}, 신뢰도={confidence:.2f}, 위치=({x1},{y1},{x2},{y2})")
```

#### 7.1.2 설정 (config.py)

```python
# app/core/config.py
class Settings(BaseSettings):
    yolo_model_path: str = "models/stamp_detector/best.pt"
    conf_thres: float = 0.05  # 검출 신뢰도
    render_dpi: int = 250     # PDF→이미지 DPI
    max_pages: int = 50       # 처리 최대 페이지
    save_debug_images: bool = False  # 디버그 이미지 저장
```

#### 7.1.3 파이프라인

```
PDF → PyMuPDF 렌더링 (250 DPI) → YOLO 검출 → 결과 JSON 반환
```

### 7.2 KoELECTRA (정책/규칙 분류)

**KoELECTRA**는 한국어 사전학습 모델로, KOICA 질의를 **정책 기반(policy)** 또는 **규칙 기반(rule_based)**으로 분류합니다.

#### 7.2.1 PolicyRuleClassifier

```python
class PolicyRuleClassifier:
    """KoELECTRA 기반 정책/규칙 분류기"""
    
    def __init__(self):
        self.model_path = "models/koelectra_policy_rule"
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_path)
        self.model = AutoModelForSequenceClassification.from_pretrained(self.model_path)
    
    def predict(self, text: str) -> Dict[str, Any]:
        """텍스트를 분류"""
        inputs = self.tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
        outputs = self.model(**inputs)
        probs = torch.softmax(outputs.logits, dim=-1)
        
        label = torch.argmax(probs, dim=-1).item()
        confidence = probs[0][label].item()
        
        return {
            "label": label,  # 0: rule_based, 1: policy
            "label_name": "rule_based" if label == 0 else "policy",
            "confidence": confidence
        }
```

#### 7.2.2 사용 사례

```python
# MCP 파이프라인에서 사용
classification = koelectra.predict("KOICA 사업의 주요 목표는 무엇인가요?")
print(classification)
# {'label': 1, 'label_name': 'policy', 'confidence': 0.92}
```

### 7.3 Exaone 3.5 (2.4B)

**Exaone**은 LG AI Research에서 개발한 한국어 특화 언어 모델입니다.

#### 7.3.1 모델 로드

```python
from artifacts.models.interfaces.base import BaseLLMModel

# 모델 로드
exaone_model = BaseLLMModel.load_model(
    model_name="lg-ai/exaone-3.5-2.4b-instruct",
    device="cuda",
    dtype="float16"
)

# QLoRA 사용 시
exaone_model = BaseLLMModel.load_model(
    model_name="lg-ai/exaone-3.5-2.4b-instruct",
    device="cuda",
    use_qlora=True,
    qlora_output_dir="models/qlora_checkpoints"
)
```

#### 7.3.2 추론

```python
messages = [
    {"role": "system", "content": "당신은 KOICA 전문가입니다."},
    {"role": "user", "content": "KOICA의 주요 사업 분야는?"}
]

response = exaone_model.invoke(messages)
print(response)
```

### 7.4 jhgan/ko-sroberta-multitask (임베딩)

**ko-sroberta**는 한국어 문장 임베딩 모델입니다 (768차원).

#### 7.4.1 임베딩 생성

```python
from sentence_transformers import SentenceTransformer

# 모델 로드
model = SentenceTransformer("jhgan/ko-sroberta-multitask")

# 임베딩 생성
texts = ["KOICA는 국제개발협력 기관입니다.", "축구 경기 일정을 알려주세요."]
embeddings = model.encode(texts)

print(embeddings.shape)  # (2, 768)
```

#### 7.4.2 벡터 검색

```python
# 쿼리 임베딩
query = "KOICA 사업 정보"
query_embedding = model.encode([query])[0]

# PostgreSQL + pgvector 검색
cursor.execute("""
    SELECT content, 1 - (embedding <=> %s::vector) AS similarity
    FROM players_embeddings
    WHERE 1 - (embedding <=> %s::vector) > 0.7
    ORDER BY embedding <=> %s::vector
    LIMIT 5
""", (query_embedding, query_embedding, query_embedding))
```

---

## 8. MCP(Model Context Protocol) 서버

### 8.1 MCP 개요

**MCP (Model Context Protocol)**는 AI 모델이 외부 도구(Tool)를 호출할 수 있도록 표준화된 인터페이스를 제공합니다.

KOICA 프로젝트에서는 **FastMCP**를 사용하여 KoELECTRA, Exaone, FileSystem을 Tool로 노출합니다.

### 8.2 KoicaMCPServer 구조

```python
class KoicaMCPServer:
    """KOICA MCP 서버 - KoElectra와 Exaone을 MCP Tool로 노출"""
    
    def __init__(self, koelectra_classifier, exaone_model, term_service):
        self._koelectra_tool = KoElectraTool(koelectra_classifier)
        self._exaone_tool = ExaoneTool(exaone_model)
        self._fs_tool = FileSystemTool()
        self._oda_term_tool = OdaTermTool(term_service)
        
        # FastMCP 서버 생성
        self._mcp = FastMCP("KOICA MCP Server")
        
        # Tool 등록
        self._mcp.tool()(self._classify_with_koelectra)
        self._mcp.tool()(self._generate_with_exaone)
        self._mcp.tool()(self._classify_and_generate)  # 파이프라인
        self._mcp.tool()(self._filesystem_list_dir)
        self._mcp.tool()(self._filesystem_read_text)
        self._mcp.tool()(self._oda_term_search)
```

### 8.3 MCP Tools

#### 8.3.1 KoElectraTool

```python
class KoElectraTool:
    """KoElectra 분류를 MCP Tool로 노출"""
    
    def classify_policy_rule(self, text: str) -> Dict[str, Any]:
        """정책/규칙 분류"""
        result = self._classifier.predict(text)
        return {
            "label": result["label"],
            "label_name": result["label_name"],
            "confidence": result["confidence"]
        }
```

#### 8.3.2 ExaoneTool

```python
class ExaoneTool:
    """Exaone 모델을 MCP Tool로 노출"""
    
    def generate_response(self, messages: list[Dict[str, str]]) -> Dict[str, Any]:
        """응답 생성"""
        if self._model is None:
            return {"response": "", "error": "모델 미로드"}
        
        response_text = self._model.invoke(messages)
        return {"response": response_text}
```

#### 8.3.3 FileSystemTool

```python
class FileSystemTool:
    """os/pathlib 기능을 MCP Tool로 노출 (Exaone이 파일 접근 가능)"""
    
    def list_dir(self, path: str = ".") -> Dict[str, Any]:
        """디렉터리 목록 반환 (data 폴더 제한)"""
        resolved = self._resolve_and_validate(path)
        entries = [{"name": name, "is_dir": full.is_dir()} 
                   for name in os.listdir(resolved)]
        return {"entries": entries}
    
    def read_text(self, path: str, encoding: str = "utf-8") -> Dict[str, Any]:
        """파일 내용 읽기"""
        resolved = self._resolve_and_validate(path)
        text = resolved.read_text(encoding=encoding)
        return {"content": text}
```

#### 8.3.4 OdaTermTool

```python
class OdaTermTool:
    """KOICA ODA 용어사전을 MCP Tool로 노출"""
    
    def search_oda_terms(self, query: str, limit: int = 3) -> Dict[str, Any]:
        """ODA 용어 검색"""
        entries = self._term_service.search_terms(query=query, limit=limit)
        return {
            "entries": [entry.to_dict() for entry in entries],
            "count": len(entries)
        }
```

### 8.4 MCP 파이프라인 (KoElectra → Exaone)

```python
def _classify_and_generate(self, question: str, system_prompt: Optional[str] = None):
    """KoElectra로 분류한 후 Exaone으로 응답 생성"""
    
    # 1) KoElectra 분류
    classification = self._koelectra_tool.classify_policy_rule(question)
    
    # 2) Exaone 응답 생성
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": question})
    
    exaone_result = self._exaone_tool.generate_response(messages)
    
    return {
        "classification": classification,
        "response": exaone_result.get("response", ""),
        "error": exaone_result.get("error")
    }
```

### 8.5 MCP 서버 실행

```python
# MCP 서버 생성
mcp_server = KoicaMCPServer(
    koelectra_classifier=classifier,
    exaone_model=exaone,
    term_service=term_service
)

# 스탠다론 실행 (stdio 모드)
if __name__ == "__main__":
    mcp_server.run(transport="stdio")
```

---

## 9. 주요 설정 (config.py)

```python
class Settings(BaseSettings):
    # 데이터베이스
    database_url: Optional[str] = None
    postgres_host: str = "ep-blue-bonus-a1zf9qhw-pooler.ap-southeast-1.aws.neon.tech"
    postgres_port: int = 5432
    postgres_user: str = "neondb_owner"
    postgres_password: str = "..."
    postgres_db: str = "neondb"
    postgres_sslmode: str = "require"
    
    # Gemini API (Fallback)
    gemini_api_key: Optional[str] = None
    gemini_model: str = "gemini-2.0-flash"
    
    # 임베딩
    embedding_dimension: int = 768
    similarity_search_limit: int = 3
    
    # 로컬 LLM
    default_chat_model: Optional[str] = "exaone-2.4b"
    model_device: str = "cuda"
    model_dtype: str = "float16"
    
    # QLoRA
    use_qlora: bool = True
    qlora_model_name: str = "lg-ai/exaone-3.5-2.4b-instruct"
    qlora_output_dir: str = "models/qlora_checkpoints"
    
    # YOLO (인감도장/서명 검출)
    yolo_model_path: str = "models/stamp_detector/best.pt"
    conf_thres: float = 0.05
    render_dpi: int = 250
    max_pages: int = 50
```

---

## 10. 데이터 흐름 예시

### 10.1 KOICA 질의 처리 흐름

```
사용자 질문: "KOICA의 주요 사업 분야는?"
    ↓
ChatOrchestrator
    ↓
QuestionClassifier → domain="koica"
    ↓
KoicaOrchestrator
    ↓
1) TermService 검색 (domain=="term"일 때만) → 미매칭
    ↓
2) KoicaTestQAService (koica_data_test.jsonl) → 미매칭
    ↓
3) KoicaMCPServer (KoElectra → Exaone 파이프라인)
    ├─ KoElectraTool.classify_policy_rule() → "policy" (0.92)
    └─ ExaoneTool.generate_response() → "KOICA의 주요 사업 분야는..."
    ↓
ChatResult 반환
    ↓
FastAPI 응답 → 사용자
```

### 10.2 RAG 기반 응답 생성 흐름

```
사용자 질문: "선수 박지성의 경력은?"
    ↓
ChatOrchestrator → SoccerOrchestrator
    ↓
LangGraph RAG 파이프라인
    ↓
[rag_search 노드]
    ├─ generate_embeddings(query) → [0.12, -0.45, ..., 0.88] (768차원)
    ├─ query_similar_documents(db_conn, query_vector, limit=3)
    │   └─ pgvector 코사인 유사도 검색
    └─ rag_context: "박지성은 대한민국 축구선수로..."
    ↓
[model 노드]
    ├─ Exaone 모델에 전달
    │   messages = [
    │       {"role": "system", "content": "참고 정보: 박지성은..."},
    │       {"role": "user", "content": "선수 박지성의 경력은?"}
    │   ]
    └─ Exaone 응답: "박지성 선수는 맨체스터 유나이티드에서..."
    ↓
ChatResult 반환
    ↓
FastAPI 응답
```

---

## 11. 핵심 기술 요약

| 기술 | 역할 | 비고 |
|------|------|------|
| **PostgreSQL + pgvector** | 벡터 임베딩 저장 및 검색 | 768차원 벡터, 코사인 유사도 |
| **LangGraph** | AI 에이전트 워크플로우 구성 | 상태 기반 그래프 실행 |
| **스타 토폴로지** | 도메인 간 느슨한 결합 | 확장성/유지보수성 향상 |
| **PyMuPDF** | PDF 텍스트/이미지 추출 | 빠른 속도, YOLO 입력 렌더링 |
| **PDFplumber** | PDF 표 추출 | PDM 매트릭스 파싱 |
| **YOLO v8** | 객체 검출 (인감도장/서명) | Ultralytics, 250 DPI 렌더링 |
| **KoELECTRA** | 정책/규칙 분류 | 한국어 사전학습 모델 |
| **Exaone 3.5 (2.4B)** | 한국어 생성 LLM | 온프레미스, QLoRA 지원 |
| **ko-sroberta** | 한국어 임베딩 (768차원) | sentence-transformers |
| **FastMCP** | MCP 서버 구축 | KoElectra, Exaone, FileSystem Tool 노출 |

---

## 12. 참고 자료

### 12.1 공식 문서

- [LangChain](https://python.langchain.com/)
- [LangGraph](https://langchain-ai.github.io/langgraph/)
- [pgvector](https://github.com/pgvector/pgvector)
- [PyMuPDF](https://pymupdf.readthedocs.io/)
- [Ultralytics YOLO](https://docs.ultralytics.com/)
- [FastMCP](https://github.com/jlowin/fastmcp)

### 12.2 내부 문서

- `docs/KOICA_RFP_EVALUATOR_TECHNICAL_DESIGN.md`: RfP 평가 시스템 설계
- `docs/SOCCER_EXAONE_EMBEDDING_PROCESS.md`: Soccer 도메인 임베딩 프로세스
- `docs/DETECT_STAMP_API.md`: 인감도장/서명 검출 API
- `README.md`: 프로젝트 전체 README

---

## 변경 이력

- **2026-02-12**: 초안 작성 (백엔드 주요 구성 기술 정리)
