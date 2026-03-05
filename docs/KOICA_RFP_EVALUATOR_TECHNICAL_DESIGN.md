# KOICA RfP 준수 평가 시스템 - 기술 설계서

## 1. Document Processing Pipeline

### 1.1 PDF Parsing Strategy

```python
# RfP 파싱: 구조화된 요구사항 추출
def parse_rfp_pdf(pdf_bytes: bytes) -> RfPDocument:
    """
    Input: RfP PDF
    Output: 구조화된 요구사항 리스트
    """
    # Step 1: 텍스트 추출
    text = extract_text_with_layout(pdf_bytes)  # PyMuPDF, 레이아웃 유지
    
    # Step 2: 요구사항 ID 패턴 추출 (정규식)
    # Pattern: CSR-001, PMR-009, FUN-004 등
    id_pattern = r'([A-Z]{3}-\d{3})'
    
    requirements = []
    for match in re.finditer(id_pattern, text):
        req_id = match.group(1)
        # ID 이후 텍스트에서 설명 추출 (다음 ID 또는 섹션 구분선까지)
        description = extract_until_next_id(text, match.end())
        
        # 카테고리 추론: ID 프리픽스로 매핑
        category = {
            'CSR': 'consulting',
            'PMR': 'project_management',
            'FUN': 'function',
            'SEC': 'security',
            'PER': 'performance',
            'DAT': 'data',
            'CAP': 'capacity_building',
        }.get(req_id[:3], 'other')
        
        requirements.append(Requirement(
            id=req_id,
            category=category,
            description=description,
            evaluation_criteria=extract_evaluation_text(description),
            deliverables=extract_deliverables(description)
        ))
    
    return RfPDocument(requirements=requirements)

# 제안서 파싱: 섹션 단위 분할
def parse_proposal_pdf(pdf_bytes: bytes) -> ProposalDocument:
    """
    Input: Proposal PDF
    Output: 계층적 섹션 리스트
    """
    # Step 1: 목차 추출 (1~5 페이지에서 "목차" 또는 "Contents" 탐지)
    toc = extract_table_of_contents(pdf_bytes)
    
    # Step 2: 섹션 헤더 기반 분할
    # "1. ", "1.1 ", "가. " 같은 번호 패턴 탐지
    sections = []
    pages = render_pdf_to_images(pdf_bytes)
    text_by_page = [extract_text(page) for page in pages]
    
    for i, page_text in enumerate(text_by_page):
        section_headers = re.findall(r'^(\d+\.\d*\.?\d*)\s+(.+)$', page_text, re.MULTILINE)
        for section_num, title in section_headers:
            content = extract_section_content(text_by_page, i, section_num)
            sections.append(ProposalSection(
                section_id=section_num,
                title=title.strip(),
                content=content,
                page_numbers=[i + 1]  # 1-based
            ))
    
    return ProposalDocument(sections=sections)
```

---

### 1.2 Data Schema (PostgreSQL + pgvector)

```sql
-- RfP 요구사항 테이블
CREATE TABLE rfp_requirements (
    id VARCHAR(10) PRIMARY KEY,              -- CSR-001
    rfp_id VARCHAR(50) NOT NULL,             -- RfP 문서 ID
    category VARCHAR(50),                     -- consulting, data, function...
    description TEXT NOT NULL,                -- 요구사항 전문
    evaluation_criteria TEXT,                 -- 평가 기준 (있으면)
    deliverables TEXT[],                      -- ["PDM", "월간보고서"]
    keywords TEXT[],                          -- ["역량강화", "워크숍", "20명"]
    embedding vector(768) NOT NULL,           -- 의미 벡터
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_rfp_req_embedding ON rfp_requirements 
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- 제안서 섹션 테이블
CREATE TABLE proposal_sections (
    id SERIAL PRIMARY KEY,
    proposal_id VARCHAR(50) NOT NULL,
    section_id VARCHAR(20),                   -- "2.3.1"
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    page_numbers INT[],
    parent_section_id VARCHAR(20),            -- 계층 구조 (2.3.1 → 2.3)
    embedding vector(768) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_proposal_section_embedding ON proposal_sections 
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- 매핑 및 평가 결과 테이블
CREATE TABLE requirement_evaluations (
    id SERIAL PRIMARY KEY,
    rfp_req_id VARCHAR(10) REFERENCES rfp_requirements(id),
    proposal_section_id INT REFERENCES proposal_sections(id),
    
    -- 매칭 점수
    id_mentioned BOOLEAN,                     -- 제안서에 요구사항 ID 명시 여부
    semantic_similarity FLOAT,                -- 0~1, 임베딩 코사인 유사도
    keyword_match_count INT,                  -- 키워드 일치 개수
    
    -- LLM 평가 결과
    compliance_status VARCHAR(20),            -- SATISFIED, PARTIAL, MISSING
    specificity_score FLOAT,                  -- 1~5
    confidence FLOAT,                         -- LLM 확신도 0~1
    evidence_text TEXT,                       -- 근거 문장 (제안서에서 인용)
    evaluator_reasoning TEXT,                 -- LLM의 판단 이유
    
    created_at TIMESTAMP DEFAULT NOW()
);

-- 최종 리포트 요약
CREATE TABLE evaluation_reports (
    id SERIAL PRIMARY KEY,
    proposal_id VARCHAR(50) UNIQUE NOT NULL,
    rfp_id VARCHAR(50) NOT NULL,
    
    total_requirements INT,
    satisfied_count INT,
    partial_count INT,
    missing_count INT,
    
    overall_score FLOAT,                      -- 0~100
    category_scores JSONB,                    -- {"consulting": 85, "data": 70, ...}
    
    critical_issues TEXT[],                   -- 치명적 누락 사항
    report_json JSONB,                        -- 전체 평가 결과
    report_generated_at TIMESTAMP DEFAULT NOW()
);
```

---

## 2. Requirement Indexing Strategy

### 2.1 임베딩 생성 전략

```python
def index_rfp_requirements(rfp_doc: RfPDocument, db_conn) -> None:
    """
    RfP 요구사항을 임베딩해 DB에 저장
    """
    from app.spokes.infrastructure.embedding_client import EmbeddingClient
    
    client = EmbeddingClient()  # jhgan/ko-sroberta-multitask
    
    for req in rfp_doc.requirements:
        # 요구사항 텍스트 구성: ID + 설명 + 평가 기준
        text = f"""
        요구사항 ID: {req.id}
        카테고리: {req.category}
        설명: {req.description}
        평가 기준: {req.evaluation_criteria or '없음'}
        산출물: {', '.join(req.deliverables) if req.deliverables else '없음'}
        """
        
        # 임베딩 생성 (768차원)
        embedding = client.get_embedding_sync(text.strip())
        
        # 키워드 추출 (명사/숫자)
        keywords = extract_keywords(req.description)  # NER 또는 형태소 분석
        
        # DB 저장
        db_conn.execute("""
            INSERT INTO rfp_requirements 
            (id, rfp_id, category, description, evaluation_criteria, 
             deliverables, keywords, embedding)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (req.id, rfp_doc.id, req.category, req.description, 
              req.evaluation_criteria, req.deliverables, keywords, embedding))

def index_proposal_sections(proposal_doc: ProposalDocument, db_conn) -> None:
    """
    제안서 섹션을 임베딩해 DB에 저장
    """
    client = EmbeddingClient()
    
    for section in proposal_doc.sections:
        # 청크 크기 제한 (512 토큰 ~ 2000자)
        content_chunk = section.content[:2000]
        
        text = f"""
        섹션: {section.section_id} {section.title}
        내용: {content_chunk}
        """
        
        embedding = client.get_embedding_sync(text.strip())
        
        db_conn.execute("""
            INSERT INTO proposal_sections 
            (proposal_id, section_id, title, content, page_numbers, 
             parent_section_id, embedding)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (proposal_doc.id, section.section_id, section.title, 
              section.content, section.page_numbers, 
              section.parent_section_id, embedding))
```

---

### 2.2 Hybrid Search Implementation

```python
def find_matching_sections(
    requirement: Requirement, 
    proposal_id: str,
    db_conn,
    top_k: int = 5
) -> List[SectionMatch]:
    """
    하이브리드 검색: ID 언급 + 의미 유사도
    """
    matches = []
    
    # [검색 1] ID 명시 탐지 (정규식)
    cursor = db_conn.execute("""
        SELECT id, section_id, title, content, page_numbers
        FROM proposal_sections
        WHERE proposal_id = %s 
          AND (content ILIKE %s OR content ~ %s)
    """, (proposal_id, f"%{requirement.id}%", rf'\b{requirement.id}\b'))
    
    explicit_mentions = cursor.fetchall()
    for row in explicit_mentions:
        matches.append(SectionMatch(
            section_id=row[0],
            similarity=1.0,  # ID 명시 = 최고 점수
            match_type='explicit_id',
            evidence=extract_sentence_with_id(row[3], requirement.id)
        ))
    
    # [검색 2] 의미 유사도 (pgvector)
    cursor = db_conn.execute("""
        SELECT id, section_id, title, content, 
               1 - (embedding <=> %s::vector) AS similarity
        FROM proposal_sections
        WHERE proposal_id = %s
        ORDER BY embedding <=> %s::vector
        LIMIT %s
    """, (requirement.embedding, proposal_id, requirement.embedding, top_k))
    
    semantic_matches = cursor.fetchall()
    for row in semantic_matches:
        if row[4] >= 0.65:  # 유사도 임계값
            matches.append(SectionMatch(
                section_id=row[0],
                similarity=row[4],
                match_type='semantic',
                evidence=row[3][:500]  # 처음 500자
            ))
    
    # [검색 3] 키워드 매칭 (보조)
    if requirement.keywords:
        keyword_query = " OR ".join([f"content ILIKE '%{kw}%'" for kw in requirement.keywords[:5]])
        cursor = db_conn.execute(f"""
            SELECT id, section_id, title, content
            FROM proposal_sections
            WHERE proposal_id = %s AND ({keyword_query})
        """, (proposal_id,))
        
        for row in cursor.fetchall():
            if row[0] not in [m.section_id for m in matches]:
                matches.append(SectionMatch(
                    section_id=row[0],
                    similarity=0.5,  # 키워드만 = 중간 점수
                    match_type='keyword'
                ))
    
    # 중복 제거 (같은 섹션이 여러 방식으로 매칭된 경우 최고 점수만)
    return deduplicate_by_section(matches, keep='highest_similarity')[:top_k]
```

---

## 3. Compliance Evaluation Logic

### 3.1 Multi-Layer Evaluation Pipeline

```
┌─────────────────────────────────────────┐
│ Layer 1: Rule-Based Pre-Filter          │
│ - ID 명시 여부 체크                      │
│ - 필수 키워드 존재 (산출물명 등)         │
│ - 페이지 수/분량 체크 (정량 요구사항)   │
│ → Pass / Warn / Fail                     │
└─────────────────────────────────────────┘
            ↓
┌─────────────────────────────────────────┐
│ Layer 2: Semantic Matching               │
│ - 임베딩 검색 (상위 5개 섹션)           │
│ - 유사도 임계값 필터링 (>= 0.65)        │
│ → Candidate Sections                     │
└─────────────────────────────────────────┘
            ↓
┌─────────────────────────────────────────┐
│ Layer 3: LLM Judgment                    │
│ - "이 섹션이 요구사항 충족하는가?"      │
│ - Compliance: Yes/Partial/No             │
│ - Specificity: 1~5                       │
│ - Evidence extraction                    │
└─────────────────────────────────────────┘
            ↓
┌─────────────────────────────────────────┐
│ Layer 4: Cross-Validation                │
│ - Rule + LLM 결과 비교                   │
│ - 불일치 시 재평가 또는 Confidence 하향 │
└─────────────────────────────────────────┘
```

---

### 3.2 Evaluation Function (Pseudo-code)

```python
def evaluate_requirement(
    requirement: Requirement,
    proposal_id: str,
    db_conn,
    llm_client
) -> EvaluationResult:
    """
    단일 요구사항에 대한 제안서 평가
    """
    # Step 1: 매칭 섹션 검색
    matches = find_matching_sections(requirement, proposal_id, db_conn, top_k=5)
    
    if not matches:
        # 매칭 없음 → 누락
        return EvaluationResult(
            req_id=requirement.id,
            status='MISSING',
            specificity=0.0,
            confidence=0.9,  # 아무것도 없으면 높은 확신으로 누락
            evidence=None,
            reasoning="제안서에서 관련 섹션을 찾을 수 없음"
        )
    
    # Step 2: Rule-based 체크
    rule_result = rule_based_check(requirement, matches)
    if rule_result.status == 'FAIL':
        return EvaluationResult(
            status='MISSING',
            specificity=0.0,
            confidence=0.8,
            reasoning=f"필수 키워드 누락: {rule_result.missing_keywords}"
        )
    
    # Step 3: LLM 평가 (상위 3개 섹션 중 가장 좋은 것)
    best_match = None
    best_score = 0
    
    for match in matches[:3]:  # 상위 3개만
        section = get_section(match.section_id, db_conn)
        
        prompt = f"""
당신은 KOICA 입찰 평가위원입니다.

[요구사항 {requirement.id}]
카테고리: {requirement.category}
설명: {requirement.description}
평가 기준: {requirement.evaluation_criteria}
필수 산출물: {requirement.deliverables}

[제안서 섹션 {section.section_id}: {section.title}]
{section.content[:1500]}

다음을 평가하세요:

1. 충족 여부
   - SATISFIED: 요구사항을 명확히 충족 (구체적 계획, 수치, 방법론 제시)
   - PARTIAL: 일부 언급만 있거나 추상적
   - MISSING: 관련 없음

2. 구체성 점수 (1~5)
   - 5: 수치, 일정, 담당자, 방법론 모두 명시
   - 3: 일반적 계획만 있음
   - 1: 키워드만 반복 (템플릿)

3. 근거 문장: 판단 근거가 되는 제안서 원문 발췌 (1~2문장)

JSON 형식으로만 답변하세요:
{{
  "status": "SATISFIED|PARTIAL|MISSING",
  "specificity": 1-5,
  "evidence": "원문 발췌",
  "reasoning": "판단 이유 1~2줄"
}}
"""
        
        response = llm_client.generate(prompt, temperature=0.1)
        result = json.loads(response)
        
        # 점수 계산: status + specificity 조합
        score = calculate_compliance_score(result['status'], result['specificity'])
        if score > best_score:
            best_score = score
            best_match = result
    
    # Step 4: Cross-validation (Rule vs LLM)
    final_confidence = best_match.get('confidence', 0.7)
    if rule_result.status == 'WARN' and best_match['status'] == 'SATISFIED':
        # Rule에서 경고인데 LLM이 OK → 신뢰도 하향
        final_confidence *= 0.8
    
    return EvaluationResult(
        req_id=requirement.id,
        status=best_match['status'],
        specificity=best_match['specificity'],
        confidence=final_confidence,
        evidence=best_match['evidence'],
        reasoning=best_match['reasoning'],
        matched_section_id=matches[0].section_id
    )

def calculate_compliance_score(status: str, specificity: float) -> float:
    """
    충족 여부 + 구체성 → 단일 점수 (0~10)
    """
    base = {'SATISFIED': 10, 'PARTIAL': 5, 'MISSING': 0}[status]
    return base * (specificity / 5.0)
```

---

### 3.3 Missing Requirement Detection

**로직**
```python
def detect_missing_requirements(evaluation_results: List[EvaluationResult]) -> List[str]:
    """
    누락된 요구사항 ID 리스트 반환
    """
    missing = []
    for result in evaluation_results:
        if result.status == 'MISSING':
            missing.append(result.req_id)
        elif result.status == 'PARTIAL' and result.specificity < 2.0:
            # Partial이지만 구체성 너무 낮으면 실질적 누락으로 간주
            missing.append(result.req_id)
    return missing
```

**False Negative 방지 (실제로는 있는데 못 찾는 경우)**
- 여러 섹션에 걸쳐 분산된 내용 → **섹션 조합 검색**: 상위 5개 섹션을 합쳐서 LLM에 전달
- "요구사항 언급은 없지만 암묵적으로 충족" → **추론 모드**: LLM에 "명시 안 했어도 다른 계획으로 커버되는가?" 질문

---

## 4. Multi-layer Validation Design

### 4.1 Rule-based Checks

```python
def rule_based_check(requirement: Requirement, matches: List[SectionMatch]) -> RuleCheckResult:
    """
    규칙 기반 1차 검증
    """
    flags = []
    
    # 체크 1: ID 명시 여부
    if not any(m.match_type == 'explicit_id' for m in matches):
        flags.append('ID_NOT_MENTIONED')
    
    # 체크 2: 필수 키워드 존재 (산출물명)
    for deliverable in requirement.deliverables:
        mentioned = any(deliverable.lower() in m.evidence.lower() for m in matches)
        if not mentioned:
            flags.append(f'DELIVERABLE_MISSING:{deliverable}')
    
    # 체크 3: 정량 요구사항 (예: "20명 이상")
    if '명' in requirement.description or '회' in requirement.description:
        numbers = extract_numbers_from_text(' '.join([m.evidence for m in matches]))
        if not numbers:
            flags.append('QUANTITATIVE_MISSING')
    
    # 판정
    if any('DELIVERABLE_MISSING' in f for f in flags):
        return RuleCheckResult(status='FAIL', flags=flags)
    elif flags:
        return RuleCheckResult(status='WARN', flags=flags)
    else:
        return RuleCheckResult(status='PASS', flags=[])
```

---

### 4.2 LLM-based Reasoning Validation

**프롬프트 설계 원칙**
1. **Few-shot Examples**: 실제 평가 사례 2~3개 예시 포함
2. **Chain-of-Thought**: "먼저 요구사항이 무엇을 요구하는지 분석, 그 다음 제안서 내용 확인, 마지막으로 충족 여부 판단"
3. **Structured Output**: JSON schema 강제 (`response_format` 옵션)
4. **Temperature 낮춤**: 0.1~0.2 (일관성 확보)

**Hallucination 방지**
```python
# 프롬프트에 명시
system_prompt = """
당신은 KOICA 평가위원입니다.
**중요**: 제안서에 명시되지 않은 내용은 추측하지 마세요.
근거 문장은 반드시 제안서 원문에서 인용해야 합니다.
불확실하면 "PARTIAL" 또는 "MISSING"으로 보수적 판단하세요.
"""

# 출력 후 검증
def validate_llm_output(result: dict, section_content: str) -> bool:
    """
    LLM이 출력한 evidence가 실제로 section_content에 있는지 검증
    """
    evidence = result.get('evidence', '')
    if not evidence:
        return False
    # 근거 문장이 섹션 내용에 포함되어 있는지 (유사도 0.9 이상)
    similarity = fuzzy_match(evidence, section_content)
    return similarity > 0.9
```

---

### 4.3 Cross-check Between Rule and LLM

```python
def cross_validate(rule_result: RuleCheckResult, llm_result: dict) -> float:
    """
    규칙 엔진과 LLM 판단 일치도 확인 → Confidence 조정
    """
    confidence = 0.7  # 기본
    
    # Case 1: Rule FAIL + LLM SATISFIED → 의심 (LLM 환각 가능성)
    if rule_result.status == 'FAIL' and llm_result['status'] == 'SATISFIED':
        confidence = 0.4  # 낮은 신뢰도
    
    # Case 2: Rule PASS + LLM SATISFIED → 강한 확신
    elif rule_result.status == 'PASS' and llm_result['status'] == 'SATISFIED':
        confidence = 0.95
    
    # Case 3: Rule WARN + LLM PARTIAL → 일치
    elif rule_result.status == 'WARN' and llm_result['status'] == 'PARTIAL':
        confidence = 0.8
    
    # Case 4: LLM MISSING + 매칭 없음 → 강한 확신으로 누락
    elif llm_result['status'] == 'MISSING' and len(matches) == 0:
        confidence = 0.95
    
    return confidence
```

---

## 5. Output Report Design

### 5.1 Requirement-by-Requirement Score

```json
{
  "proposal_id": "PROP-2026-001",
  "rfp_id": "RFP-KOICA-2026-PMC",
  "evaluated_at": "2026-02-10T15:30:00Z",
  
  "summary": {
    "total_requirements": 62,
    "satisfied": 45,
    "partial": 10,
    "missing": 7,
    "overall_score": 78.5,
    "category_scores": {
      "consulting": 82.0,
      "data": 75.0,
      "project_management": 68.0,
      "security": 90.0
    }
  },
  
  "requirements": [
    {
      "id": "CSR-001",
      "category": "consulting",
      "description": "수원국 공무원 20명 이상 대상 월 1회 역량 강화 워크숍",
      "status": "SATISFIED",
      "specificity": 4.2,
      "confidence": 0.88,
      "matched_section": "2.3.1 역량 강화 계획",
      "evidence": "월 2회 워크숍 개최, 참석자 25명, 4시간 진행, 만족도 설문 실시",
      "reasoning": "요구사항(월 1회, 20명)을 초과 달성하는 구체적 계획 제시",
      "page_numbers": [15, 16]
    },
    {
      "id": "PMR-009",
      "category": "project_management",
      "description": "PDM(Project Design Matrix) 매트릭스 제출",
      "status": "MISSING",
      "specificity": 0.0,
      "confidence": 0.92,
      "matched_section": null,
      "evidence": null,
      "reasoning": "제안서에서 'PDM' 키워드 미발견, 유사 섹션도 없음"
    }
  ],
  
  "missing_critical": [
    "PMR-009: PDM 매트릭스",
    "FUN-004: 데이터 백업 계획"
  ],
  
  "warnings": [
    "CSR-005: 일정 명시 없음 (PARTIAL, specificity 2.1)"
  ]
}
```

---

### 5.2 Markdown Report Template

```markdown
# 제안서 평가 리포트

**제안서 ID**: PROP-2026-001  
**RfP**: RFP-KOICA-2026-PMC  
**평가 일시**: 2026-02-10 15:30

---

## 종합 점수: 78.5 / 100

| 카테고리 | 점수 | 충족 | 부분 | 누락 |
|----------|------|------|------|------|
| 컨설팅 방법론 | 82.0 | 15 | 3 | 2 |
| 프로젝트 관리 | 68.0 | 10 | 4 | 6 |
| 데이터/기술 | 75.0 | 12 | 2 | 1 |
| 보안 | 90.0 | 8 | 0 | 0 |

---

## ⚠️ 치명적 누락 사항 (7개)

1. **PMR-009**: PDM 매트릭스 미제출
   - 근거: 제안서 전체에서 "PDM" 키워드 미발견
   - 페이지: 없음
   - 권장: 섹션 2.4에 PDM 표 추가 필요

2. **FUN-004**: 데이터 백업 계획 미명시
   - 근거: "백업" 언급은 있으나(p.23) 구체적 주기/방법 없음
   - 권장: 일일 백업, 오프사이트 저장 계획 추가

...

---

## 🟡 개선 권장 사항 (10개, Partial)

1. **CSR-005**: 일정 구체성 부족 (specificity 2.1)
   - 현재: "분기별 점검" (추상적)
   - 권장: "1/4/7/10월 셋째 주 금요일 오후 2시" (구체적)

...

---

## ✅ 강점 (45개 충족)

- CSR-001~015: 컨설팅 방법론 우수 (평균 specificity 4.1)
- SEC-001~008: 보안 계획 완벽 (모두 SATISFIED)

---

## 부록: 요구사항별 상세 평가

### CSR-001: 역량 강화 워크숍
- **상태**: ✅ SATISFIED
- **구체성**: 4.2 / 5.0
- **근거**: "월 2회 워크숍 개최, 참석자 25명..." (p.15)
- **매칭 섹션**: 2.3.1 역량 강화 계획
- **Confidence**: 88%

...
```

---

## 6. Failure Mode Analysis

### 6.1 False Positives (오탐: 실제로는 미충족인데 충족으로 판정)

**원인**
1. **키워드만 언급**: "PDM을 작성합니다" (실제 PDM 표 없음)
2. **템플릿 복붙**: 모든 요구사항에 "~을 수행합니다" 반복

**대응**
```python
def detect_template_reuse(section_content: str, all_sections: List[str]) -> bool:
    """
    템플릿 재사용 탐지
    """
    # 1. n-gram 중복도
    for other in all_sections:
        if jaccard_similarity(section_content, other) > 0.8:
            return True  # 80% 이상 중복 → 템플릿
    
    # 2. 일반 동사 비율
    generic_verbs = ['수행합니다', '진행합니다', '실시합니다', '예정입니다']
    verb_ratio = count_generic_verbs(section_content) / total_sentences
    if verb_ratio > 0.7:
        return True  # 70% 이상이 일반 동사 → 공허
    
    # 3. 구체적 entity 부재
    has_numbers = bool(re.search(r'\d+', section_content))
    has_dates = bool(re.search(r'\d{4}[-./]\d{1,2}', section_content))
    has_names = extract_named_entities(section_content)  # NER
    if not (has_numbers or has_dates or has_names):
        return True  # 숫자/날짜/고유명사 없음 → 템플릿
    
    return False

# 템플릿 탐지 시 처리
if detect_template_reuse(section.content, all_sections):
    specificity = min(specificity, 2.0)  # 최대 2점으로 제한
    confidence *= 0.7  # 신뢰도 하향
```

---

### 6.2 False Negatives (실제로는 충족인데 누락으로 판정)

**원인**
1. **분산 서술**: 요구사항이 여러 섹션에 나뉘어 기술됨
2. **암묵적 충족**: ID는 안 써도 실질적으로 커버함

**대응**
```python
# 재검증 로직
def revalidate_missing(
    requirement: Requirement, 
    proposal_id: str,
    db_conn,
    llm_client
) -> bool:
    """
    MISSING으로 판정된 요구사항을 제안서 전체 맥락에서 재평가
    """
    # 상위 10개 섹션 합쳐서 다시 LLM에 질문
    top_sections = find_matching_sections(requirement, proposal_id, db_conn, top_k=10)
    combined_text = '\n\n'.join([s.evidence for s in top_sections[:5]])
    
    prompt = f"""
요구사항: {requirement.description}

제안서 주요 섹션들:
{combined_text}

위 섹션들을 종합했을 때, 요구사항이 **암묵적으로라도** 충족되는가?
(명시적 언급 없어도 실질적으로 같은 효과를 내는 계획이 있으면 Yes)

답변: Yes / No / Uncertain
이유: 1줄
"""
    
    response = llm_client.generate(prompt)
    if 'Yes' in response:
        return True  # 누락 아님, PARTIAL로 상향
    return False
```

---

### 6.3 Generic Template Reuse Detection

**고도화 전략**
```python
def specificity_score_llm(section_content: str, requirement_desc: str) -> float:
    """
    LLM으로 구체성 점수 산출 (1~5)
    """
    prompt = f"""
요구사항: {requirement_desc}
제안서 내용: {section_content}

구체성 점수 (1~5):
- 5: 수치(인원/횟수/금액), 일정(월/일), 담당자, 방법론, 평가 방법 모두 명시
- 4: 위 중 3~4개 명시
- 3: 일반적 계획만 ("~을 실시합니다")
- 2: 추상적 언급 ("~을 고려합니다")
- 1: 요구사항 키워드만 복사 (템플릿)

점수와 이유를 JSON으로:
{{"score": 1-5, "reason": "..."}}
"""
    
    result = json.loads(llm_client.generate(prompt, temperature=0.1))
    
    # 검증: score가 4~5인데 숫자/날짜가 없으면 의심
    if result['score'] >= 4:
        has_concrete = bool(re.search(r'\d+', section_content))
        if not has_concrete:
            result['score'] = max(3.0, result['score'] - 1.5)  # 하향 조정
    
    return result['score']
```

---

## 7. Model Orchestration

### 7.1 When to Use Small Models vs LLM

| 작업 | 모델 | 이유 |
|------|------|------|
| **섹션 카테고리 분류** | KoELECTRA-small (로컬) | 빠름, 5~10개 클래스 분류만 하면 됨 |
| **키워드 추출** | 형태소 분석기 (KoNLPy) | LLM 불필요, 규칙 기반으로 충분 |
| **임베딩 생성** | ko-sroberta (로컬) | 검색용, 로컬 768차원으로 충분 |
| **충족 여부 판단** | GPT-4o / Gemini-1.5 Pro | 추론 필요, 긴 컨텍스트(제안서 섹션 1500자) |
| **구체성 점수** | GPT-4o | 미묘한 뉘앙스 판단 필요 |
| **리포트 생성** | GPT-4o | 자연어 생성 품질 |

---

### 7.2 Cost Control Strategy

```python
# 비용 최적화: LLM 호출 최소화
def evaluate_all_requirements(
    requirements: List[Requirement],
    proposal_id: str,
    db_conn,
    llm_client,
    budget_limit: float = 3.0  # USD
) -> List[EvaluationResult]:
    """
    LLM 호출 비용 제어하며 평가
    """
    results = []
    cost_spent = 0.0
    
    for req in requirements:
        # Step 1: Rule-based 체크 (무료)
        matches = find_matching_sections(req, proposal_id, db_conn)
        rule_result = rule_based_check(req, matches)
        
        # 명확한 경우 LLM 생략
        if rule_result.status == 'FAIL' and len(matches) == 0:
            # 매칭 없음 + Rule FAIL → LLM 호출 없이 MISSING
            results.append(EvaluationResult(
                req_id=req.id, status='MISSING', 
                specificity=0, confidence=0.9
            ))
            continue
        
        if req.id in matches and matches[0].match_type == 'explicit_id' and matches[0].similarity == 1.0:
            # ID 명시 + Rule PASS → LLM 생략하고 SATISFIED (비용 절감)
            results.append(EvaluationResult(
                req_id=req.id, status='SATISFIED',
                specificity=3.5,  # 보수적 기본값
                confidence=0.75
            ))
            continue
        
        # Step 2: LLM 판단 (비용 발생)
        if cost_spent >= budget_limit:
            # 예산 초과 시 남은 요구사항은 규칙 기반만
            results.append(EvaluationResult(
                req_id=req.id, status='PARTIAL',
                confidence=0.5, reasoning="LLM 예산 초과로 규칙 기반만 평가"
            ))
            continue
        
        llm_result = llm_evaluate(req, matches, llm_client)
        cost_spent += estimate_llm_cost(llm_result.tokens_used)
        results.append(llm_result)
    
    return results
```

**예상 비용 (GPT-4o 기준)**
- 요구사항 60개 × 평균 2,000 토큰(입력) + 200 토큰(출력) = 132,000 토큰
- GPT-4o: $2.50 / 1M input, $10 / 1M output
- **총 비용**: ~$0.50 / 제안서

**최적화 적용 시**
- 명확한 경우(30%) LLM 생략 → 40개만 LLM 호출
- **비용**: ~$0.35 / 제안서

---

## 8. Step-by-Step Evaluation Pipeline

```python
# 전체 파이프라인
async def evaluate_proposal_against_rfp(
    rfp_pdf_path: str,
    proposal_pdf_path: str,
    db_conn,
    llm_client
) -> EvaluationReport:
    """
    End-to-end 평가 파이프라인
    """
    # ===== Phase 1: Document Ingestion =====
    rfp_doc = parse_rfp_pdf(read_pdf(rfp_pdf_path))
    proposal_doc = parse_proposal_pdf(read_pdf(proposal_pdf_path))
    
    rfp_id = f"RFP-{uuid.uuid4().hex[:8]}"
    proposal_id = f"PROP-{uuid.uuid4().hex[:8]}"
    
    # ===== Phase 2: Indexing =====
    index_rfp_requirements(rfp_doc, db_conn)
    index_proposal_sections(proposal_doc, db_conn)
    
    # ===== Phase 3: Evaluation (병렬 처리 가능) =====
    evaluation_tasks = [
        evaluate_requirement(req, proposal_id, db_conn, llm_client)
        for req in rfp_doc.requirements
    ]
    results = await asyncio.gather(*evaluation_tasks)  # 동시 평가
    
    # ===== Phase 4: Aggregation =====
    summary = aggregate_results(results)
    missing = detect_missing_requirements(results)
    
    # ===== Phase 5: Report Generation =====
    report = EvaluationReport(
        proposal_id=proposal_id,
        rfp_id=rfp_id,
        summary=summary,
        requirements=results,
        missing_critical=missing,
        warnings=extract_warnings(results)
    )
    
    # DB 저장
    save_report(report, db_conn)
    
    return report

# 집계 로직
def aggregate_results(results: List[EvaluationResult]) -> Summary:
    """
    개별 평가 결과 → 종합 점수
    """
    by_category = {}
    for r in results:
        cat = r.requirement.category
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(r)
    
    category_scores = {}
    for cat, reqs in by_category.items():
        # 카테고리 점수: (SATISFIED*10 + PARTIAL*5) / (요구사항수*10)
        total = sum(
            10 if r.status == 'SATISFIED' else 5 if r.status == 'PARTIAL' else 0
            for r in reqs
        )
        max_possible = len(reqs) * 10
        category_scores[cat] = (total / max_possible) * 100
    
    overall_score = sum(category_scores.values()) / len(category_scores)
    
    return Summary(
        total_requirements=len(results),
        satisfied=sum(1 for r in results if r.status == 'SATISFIED'),
        partial=sum(1 for r in results if r.status == 'PARTIAL'),
        missing=sum(1 for r in results if r.status == 'MISSING'),
        overall_score=overall_score,
        category_scores=category_scores
    )
```

---

## 9. Implementation Modules

### 9.1 폴더 구조

```
app/
├── domain/
│   ├── rfp/
│   │   ├── parsers/
│   │   │   ├── rfp_pdf_parser.py          # PDF → 요구사항 추출
│   │   │   └── requirement_extractor.py   # ID 패턴 파싱
│   │   ├── repositories/
│   │   │   └── requirement_repository.py  # DB CRUD
│   │   └── schemas/
│   │       └── rfp_schema.py              # Requirement, RfPDocument
│   │
│   ├── proposal/
│   │   ├── parsers/
│   │   │   ├── proposal_pdf_parser.py     # PDF → 섹션 분할
│   │   │   └── toc_extractor.py           # 목차 추출
│   │   ├── repositories/
│   │   │   └── section_repository.py
│   │   └── schemas/
│   │       └── proposal_schema.py
│   │
│   └── evaluation/
│       ├── services/
│       │   ├── matcher.py                 # 요구사항-섹션 매칭
│       │   ├── rule_validator.py          # 규칙 기반 체크
│       │   ├── llm_evaluator.py           # LLM 평가
│       │   └── report_generator.py        # 리포트 생성
│       ├── orchestrators/
│       │   └── evaluation_orchestrator.py # 전체 파이프라인
│       └── schemas/
│           └── evaluation_schema.py
│
├── api/
│   └── v1/
│       └── evaluation/
│           └── evaluation_router.py       # FastAPI 엔드포인트
│
└── spokes/
    └── infrastructure/
        └── embedding_client.py            # 기존 사용 (jhgan/ko-sroberta)
```

---

### 9.2 API Endpoints

```python
# app/api/v1/evaluation/evaluation_router.py

@router.post("/upload-rfp")
async def upload_rfp(file: UploadFile) -> dict:
    """
    RfP PDF 업로드 → 파싱 → DB 저장
    """
    pdf_bytes = await file.read()
    rfp_doc = parse_rfp_pdf(pdf_bytes)
    rfp_id = save_rfp(rfp_doc, db_conn)
    index_rfp_requirements(rfp_doc, db_conn)
    return {"rfp_id": rfp_id, "requirements_count": len(rfp_doc.requirements)}

@router.post("/upload-proposal")
async def upload_proposal(
    file: UploadFile,
    rfp_id: str
) -> dict:
    """
    제안서 PDF 업로드 → 파싱 → DB 저장
    """
    pdf_bytes = await file.read()
    proposal_doc = parse_proposal_pdf(pdf_bytes)
    proposal_id = save_proposal(proposal_doc, rfp_id, db_conn)
    index_proposal_sections(proposal_doc, db_conn)
    return {"proposal_id": proposal_id, "sections_count": len(proposal_doc.sections)}

@router.post("/evaluate/{proposal_id}")
async def run_evaluation(proposal_id: str, background_tasks: BackgroundTasks) -> dict:
    """
    평가 실행 (비동기 작업)
    """
    job_id = f"eval-{uuid.uuid4().hex[:8]}"
    background_tasks.add_task(
        evaluate_proposal_against_rfp_async,
        proposal_id, job_id, db_conn, llm_client
    )
    return {"job_id": job_id, "status": "started"}

@router.get("/report/{proposal_id}")
async def get_evaluation_report(proposal_id: str) -> EvaluationReport:
    """
    평가 리포트 조회 (JSON)
    """
    report = load_report(proposal_id, db_conn)
    if not report:
        raise HTTPException(404, "Report not found")
    return report
```

---

## 10. Confidence Score Calculation

```python
def calculate_final_confidence(
    rule_result: RuleCheckResult,
    llm_result: dict,
    semantic_similarity: float,
    id_mentioned: bool
) -> float:
    """
    최종 신뢰도 산출 (0~1)
    """
    base = 0.5
    
    # Factor 1: ID 명시 (+0.3)
    if id_mentioned:
        base += 0.3
    
    # Factor 2: 의미 유사도 (0~0.2)
    base += semantic_similarity * 0.2
    
    # Factor 3: Rule vs LLM 일치도
    if rule_result.status == 'PASS' and llm_result['status'] == 'SATISFIED':
        base += 0.2  # 일치 → 높은 신뢰
    elif rule_result.status == 'FAIL' and llm_result['status'] == 'SATISFIED':
        base -= 0.3  # 불일치 → 낮은 신뢰 (LLM 환각 의심)
    
    # Factor 4: Specificity (구체성 높으면 신뢰도 상승)
    specificity_bonus = (llm_result.get('specificity', 3) - 3) * 0.05
    base += specificity_bonus
    
    return max(0.0, min(1.0, base))  # 0~1로 클램핑
```

---

## 11. 실행 가능한 최소 구현 (MVP)

### Step 1: RfP 수동 JSON 작성 (자동 파싱은 Phase 2)

```json
// data/rfp_samples/koica_pmc_2026.json
{
  "rfp_id": "RFP-KOICA-2026-PMC",
  "title": "키르기스스탄 PMC 사업",
  "requirements": [
    {
      "id": "CSR-001",
      "category": "consulting",
      "description": "수원국 공무원 20명 이상 대상 월 1회 이상 역량 강화 워크숍 실시",
      "evaluation_criteria": "참석자 수, 횟수, 교육 내용 구체성",
      "deliverables": ["워크숍 결과보고서", "참석자 명단"],
      "keywords": ["역량강화", "워크숍", "20명", "월 1회"]
    },
    // ... 60개
  ]
}
```

---

### Step 2: 제안서 파싱 (목차 기반 섹션 분할)

```python
# app/domain/proposal/parsers/proposal_pdf_parser.py

def parse_proposal_simple(pdf_bytes: bytes) -> List[ProposalSection]:
    """
    간단한 섹션 분할: 번호 패턴 기반
    """
    text = extract_text_with_pages(pdf_bytes)  # {page_num: text}
    sections = []
    
    # "1. ", "1.1 ", "2.3.1 " 같은 패턴
    pattern = r'^(\d+(?:\.\d+)*)\s+(.+)$'
    
    for page_num, page_text in text.items():
        for match in re.finditer(pattern, page_text, re.MULTILINE):
            section_id = match.group(1)
            title = match.group(2).strip()
            
            # 다음 섹션까지의 내용 (간단히 500자 또는 다음 헤더까지)
            content = extract_content_after_header(page_text, match.end(), max_chars=2000)
            
            sections.append(ProposalSection(
                section_id=section_id,
                title=title,
                content=content,
                page_numbers=[page_num]
            ))
    
    return sections
```

---

### Step 3: 평가 실행 (단일 스레드 버전)

```python
# app/domain/evaluation/orchestrators/evaluation_orchestrator.py

def run_evaluation(rfp_id: str, proposal_id: str, db_conn, llm_client) -> EvaluationReport:
    """
    전체 평가 파이프라인
    """
    # Load
    requirements = load_requirements(rfp_id, db_conn)
    
    results = []
    for req in requirements:
        # 1) 매칭
        matches = find_matching_sections(req, proposal_id, db_conn, top_k=5)
        
        # 2) 규칙 체크
        rule = rule_based_check(req, matches)
        
        # 3) LLM 평가 (필요 시)
        if should_use_llm(rule, matches):
            llm_result = llm_evaluate(req, matches, llm_client)
            confidence = cross_validate(rule, llm_result, matches)
            results.append(EvaluationResult(
                req_id=req.id,
                status=llm_result['status'],
                specificity=llm_result['specificity'],
                confidence=confidence,
                evidence=llm_result['evidence'],
                reasoning=llm_result['reasoning']
            ))
        else:
            # Rule만으로 판단
            results.append(rule_only_result(req, rule, matches))
    
    # 4) 집계
    summary = aggregate_results(results)
    
    # 5) 리포트 생성
    report = generate_report(proposal_id, rfp_id, results, summary)
    save_report(report, db_conn)
    
    return report
```

---

## 12. Failure Mode Mitigation

### 12.1 False Positive 방지

```python
# 오탐 감지: "키워드만 있고 실체 없음"
def validate_deliverable_presence(
    requirement: Requirement,
    section: ProposalSection
) -> bool:
    """
    산출물이 실제로 제시되었는지 검증
    """
    if 'PDM' in requirement.deliverables:
        # "PDM" 키워드만 있고 표가 없으면 False
        has_table = detect_table_in_text(section.content)  # "|" 또는 탭 패턴
        if not has_table and 'PDM' in section.content:
            return False  # 키워드만 언급, 실제 표 없음
    
    # 숫자 요구사항: "20명 이상" → 제안서에 숫자 있는지
    required_numbers = extract_numbers(requirement.description)
    proposal_numbers = extract_numbers(section.content)
    if required_numbers and not proposal_numbers:
        return False
    
    return True
```

---

### 12.2 False Negative 방지

```python
# 누락 오판 방지: 분산 서술 재검증
def revalidate_missing_with_context(
    requirement: Requirement,
    proposal_id: str,
    db_conn,
    llm_client
) -> Optional[EvaluationResult]:
    """
    MISSING으로 판정된 요구사항 재평가
    """
    # 전체 제안서 요약에서 찾기
    proposal_summary = get_proposal_summary(proposal_id, db_conn)  # 전체 섹션 제목 리스트
    
    prompt = f"""
요구사항: {requirement.description}

제안서 전체 구성 (섹션 제목):
{chr(10).join([f"{s.section_id} {s.title}" for s in proposal_summary])}

이 요구사항이 어느 섹션에서 다루어질 가능성이 있나요?
답변: 섹션 번호 또는 "없음"
"""
    
    response = llm_client.generate(prompt)
    if '없음' not in response:
        # LLM이 가능성 있는 섹션 제시 → 해당 섹션 다시 읽고 재평가
        suggested_section_id = extract_section_id(response)
        section = get_section_by_id(suggested_section_id, proposal_id, db_conn)
        return evaluate_requirement_with_section(requirement, section, llm_client)
    
    return None  # 여전히 누락
```

---

### 12.3 LLM Hallucination Control

**전략**
1. **Grounding**: 근거 문장을 제안서 원문에서 반드시 인용하도록 강제
2. **검증**: 출력된 evidence가 실제 섹션 content에 존재하는지 fuzzy match
3. **Conservative Prompting**: "불확실하면 PARTIAL 또는 MISSING으로 판단"

```python
def validate_llm_evidence(evidence: str, section_content: str) -> bool:
    """
    LLM이 출력한 근거가 실제 섹션에 있는지 검증
    """
    from difflib import SequenceMatcher
    
    # 근거 문장이 섹션 내용의 일부와 90% 이상 일치하는지
    for sentence in split_sentences(section_content):
        similarity = SequenceMatcher(None, evidence, sentence).ratio()
        if similarity > 0.9:
            return True
    
    return False

# 검증 실패 시 재시도
if not validate_llm_evidence(llm_result['evidence'], section.content):
    # 근거가 환각 → PARTIAL로 하향, confidence 0.3
    llm_result['status'] = 'PARTIAL'
    llm_result['confidence'] = 0.3
    llm_result['reasoning'] += " (근거 검증 실패)"
```

---

## 13. Configuration & Thresholds

```python
# app/core/config.py 추가

class Settings(BaseSettings):
    # ... 기존 설정 ...
    
    # RfP 평가 관련
    evaluation_similarity_threshold: float = 0.65  # 의미 유사도 최소값
    evaluation_specificity_min: float = 2.0        # 구체성 최소 (PARTIAL 기준)
    evaluation_confidence_min: float = 0.7         # 신뢰도 최소 (리포트 포함 기준)
    evaluation_llm_temperature: float = 0.1        # LLM 일관성 확보
    evaluation_max_llm_calls: int = 100            # 비용 제어 (제안서당)
```

---

## 14. Testing & Validation Strategy

### 14.1 Unit Tests

```python
# tests/test_evaluation.py

def test_requirement_extraction():
    """
    RfP PDF에서 요구사항 ID 추출 테스트
    """
    sample_text = """
    CSR-001: 수원국 공무원 20명 이상 대상 교육
    CSR-002: 월간 진행 보고서 제출
    """
    reqs = extract_requirements_from_text(sample_text)
    assert len(reqs) == 2
    assert reqs[0].id == "CSR-001"
    assert "20명" in reqs[0].description

def test_template_detection():
    """
    템플릿 재사용 탐지 테스트
    """
    section1 = "~를 수행합니다. ~를 진행합니다. ~를 실시합니다."
    section2 = "~를 수행합니다. ~를 진행합니다. ~를 완료합니다."
    assert detect_template_reuse(section1, [section2]) == True

def test_missing_detection():
    """
    누락 탐지 정확도 테스트
    """
    # Ground truth: CSR-005는 제안서에 없음
    results = evaluate_proposal_against_rfp(rfp_id, proposal_id, db_conn, llm_client)
    missing = [r.req_id for r in results if r.status == 'MISSING']
    assert 'CSR-005' in missing
```

---

### 14.2 Integration Test (실제 평가자 vs AI)

```python
# tests/test_evaluator_agreement.py

def test_human_vs_ai_correlation():
    """
    실제 평가자 점수 vs AI 점수 상관계수 측정
    """
    test_cases = load_test_proposals_with_human_scores()  # 10건
    
    ai_scores = []
    human_scores = []
    
    for case in test_cases:
        ai_report = evaluate_proposal_against_rfp(case.rfp_id, case.proposal_id, ...)
        ai_scores.append(ai_report.summary.overall_score)
        human_scores.append(case.human_score)
    
    from scipy.stats import pearsonr
    correlation, p_value = pearsonr(ai_scores, human_scores)
    
    assert correlation > 0.7, f"상관계수 너무 낮음: {correlation}"
    print(f"AI vs 평가자 상관계수: {correlation:.3f}")
```

---

## 15. 현재 프로젝트 통합 방안

### 기존 인프라 재사용
- ✅ `jhgan/ko-sroberta-multitask` (임베딩) → 그대로 사용
- ✅ `pgvector` (PostgreSQL) → 요구사항·섹션 임베딩 저장
- ✅ `FastAPI` → 새 라우터 추가 (`/api/v1/evaluation`)
- ✅ `PyMuPDF` → PDF 파싱 (detect에서 이미 사용 중)
- ✅ `Exaone` (선택) → LLM 온프레미스 옵션

### 새로 추가할 것
1. **DB 마이그레이션**
   ```bash
   alembic revision --autogenerate -m "add rfp and evaluation tables"
   alembic upgrade head
   ```

2. **도메인 로직**
   ```
   app/domain/rfp/
   app/domain/proposal/
   app/domain/evaluation/
   ```

3. **프론트엔드**
   ```
   www.ohgun.site/app/evaluation/page.tsx
   ```
   - RfP 업로드 → 제안서 업로드 → 평가 시작 → 리포트 다운로드

---

## 16. Quick Start Implementation Order

### Week 1-2: 핵심 파싱
- [ ] `rfp_pdf_parser.py` (정규식 기반 ID 추출)
- [ ] `proposal_pdf_parser.py` (섹션 헤더 파싱)
- [ ] DB 스키마 생성 (requirements, sections, evaluations)

### Week 3-4: 매칭 엔진
- [ ] `matcher.py` (임베딩 검색 + ID 탐지)
- [ ] `rule_validator.py` (키워드 체크)
- [ ] 테스트: 요구사항 1개 → 섹션 매칭 성공

### Week 5-6: LLM 평가
- [ ] `llm_evaluator.py` (프롬프트 설계)
- [ ] 환각 방지 검증 로직
- [ ] 테스트: 10개 요구사항 평가 정확도

### Week 7-8: 리포트 + API
- [ ] `report_generator.py` (JSON + Markdown)
- [ ] FastAPI 라우터
- [ ] 프론트엔드 UI (간단한 업로드·다운로드)

**총 소요**: 약 2개월 (1~2명)

---

## 17. 핵심 기술 스택

| 구성 요소 | 기술 | 현재 프로젝트 | 비고 |
|-----------|------|---------------|------|
| PDF 파싱 | PyMuPDF | ✅ 사용 중 (detect) | 그대로 재사용 |
| 임베딩 | jhgan/ko-sroberta | ✅ 사용 중 (soccer) | 그대로 재사용 |
| 벡터 검색 | pgvector | ✅ 사용 중 | 그대로 재사용 |
| LLM | GPT-4o / Exaone | ✅ Exaone 있음 | 온프레미스 or API |
| 백엔드 | FastAPI | ✅ 사용 중 | 라우터 추가 |
| 프론트 | Next.js | ✅ 사용 중 | 페이지 추가 |
| DB | PostgreSQL | ✅ 사용 중 | 테이블 추가 |

**추가 설치 필요 없음** → 현재 스택으로 바로 구현 가능

---

## 18. Critical Implementation Notes

### PDF 파싱 실패 대응
- **OCR Fallback**: PyMuPDF로 텍스트 추출 안 되면 Tesseract OCR
- **표 파싱**: Camelot 또는 Tabula로 PDM 매트릭스 같은 표 추출

### 임베딩 차원 일치
- 현재 프로젝트: 768차원 (jhgan/ko-sroberta)
- players_embeddings 테이블도 vector(768) → **일치**, 그대로 사용 가능

### LLM Context Length
- 제안서 섹션이 긴 경우(5페이지 이상) → 2000자로 truncate 또는 요약 후 전달
- GPT-4o: 128K context → 섹션 5개 동시 전달 가능

### 한국어 NER
- 키워드 추출: KoNLPy (형태소 분석) + 명사 추출
- 고급: KoBERT NER 모델 (인명, 기관명 추출)

---

## 결론

**구현 복잡도**: ⭐⭐⭐☆☆ (중상)  
- PDF 파싱: 중간 (정규식 + OCR fallback)
- 매칭 엔진: 쉬움 (pgvector 이미 사용 중)
- LLM 평가: 중간 (프롬프트 엔지니어링 + 검증)

**기술 스택 준비도**: ⭐⭐⭐⭐⭐ (완료)  
- 현재 프로젝트에 필요한 것 모두 있음

**권장 시작 순서**
1. RfP 1건 수동 JSON 작성 (1일)
2. 제안서 파싱 (1주)
3. 매칭 + 규칙 체크 (1주)
4. LLM 평가 (2주)
5. 리포트 (1주)

**총 MVP 일정**: 6~8주
