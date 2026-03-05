# RMI CMRT 6.5 자동화 AI 에이전트 전략 설계

> 구현은 보류. 추후 참고용으로 전략·구조만 문서화.

---

## 1. 목표

공급망에서 수집된 로우 데이터(송장, 기존 보고서, 텍스트 등)를 분석하여 **RMI CMRT 6.5** 엑셀 템플릿의 각 항목을 자동으로 채워주는 AI 에이전트를 만드는 것.

---

## 2. CMRT 6.5 파일 구조 분석 결과

### 2.1 시트 목록

- Revision, Instructions, Definitions  
- **Declaration** (선언 시트)  
- **Smelter List** (제련소 입력 시트)  
- **Checker** (검증 로직 시트)  
- Product List  
- **Smelter Look-up** (표준 제련소 참조 데이터)  
- L, C, SorP (기타)

### 2.2 핵심 시트 구조

| 시트 | 크기 | 비고 |
|------|------|------|
| **Declaration** | 119행 x 18열 | 회사 정보(7–21행), 질문 1–7(24–60행), 4가지 광물별 Yes/No |
| **Smelter List** | 2,504행 x 34열 | 행 3 헤더, 행 4부터 입력, 드롭다운 사용 |
| **Smelter Look-up** | 641행 x 11열 | 행 4부터 데이터. Metal, Smelter Look-up(*), Standard Smelter Names, Country, **Smelter ID(CID)** |
| **Checker** | 50행 x 10열 | 논리 검증 수식, 필수 항목 체크 |
| **Product List** | 5행 x 4열 | Scope가 Product일 때 작성 |

### 2.3 Smelter Look-up 열 구조

- `[0]` Metal (Gold / Tin / Tantalum / Tungsten)
- `[1]` Smelter Look-up (*) — 별칭/통칭 (검색용)
- `[2]` Standard Smelter Names — 공식 표준 명칭
- `[3]` Smelter Facility Location: Country
- `[4]` Smelter ID — CID (예: CID002763)

---

## 3. 전략 설계

### 3.1 제련소 매칭 로직 (Smelter Matching)

**Source**: `Smelter Look-up` 시트의 표준 데이터.

**로직**  
- 공급사 데이터의 제련소 명칭·CID를 **임베딩 유사도**로 비교.  
- **기존 프로젝트의 `SemanticFieldMatcher`(dragonkue/multilingual-e5-small-ko-v2) 재사용** 권장.

**Guardrail**

1. **CID 일치** → 최우선 매칭.
2. **명칭 유사도 < 0.9** → 자동 입력하지 않고 **'Manual Review Required'** 플래그.
3. 매칭 시 **Smelter List 시트 드롭다운 값과 동일한 문자열**로만 입력.

**알고리즘 요약**

1. **STEP 1**: 입력에 CID가 있으면 Look-up에서 CID로 exact match → 해당 Standard Name 반환, 종료.
2. **STEP 2**: 쿼리 `"{metal} {smelter_name} {country}"` 로 임베딩 검색, Top-5 후보.
3. **STEP 3**:  
   - 유사도 ≥ 0.90 → 자동 매칭.  
   - 0.70 ≤ 유사도 < 0.90 → Manual Review.  
   - < 0.70 → Not Found.

**드롭다운 정합성**  
- openpyxl로 해당 열의 data validation 확인.  
- 매칭된 standard_name이 드롭다운 리스트에 있는지 검증 후 입력.

---

### 3.2 선언 시트 논리적 일관성 (Declaration Logic)

**의존성**  
- 질문 1~7은 상호 의존.  
- 예: 1번(광물 사용 여부)이 'No'면 해당 광물의 이후 답변은 'N/A' 또는 논리적으로 고정.

**검증**  
- AI가 생성한 답변이 **Checker 시트 로직**을 통과하는지 시뮬레이션하는 **검증 함수** 구현.
- 예: Q1=No → Q2~Q7은 N/A; Q5=Yes → Q4=Yes 필수; Q2=Yes → Q6, Q7 필수 등.

**자동 보정**  
- RAG로 소스 문서 검색 후 LLM(Gemini)이 Q1~7에 대한 Yes/No/Unknown 생성.  
- 검증 오류 시 재시도 또는 수정 제안(LLM 활용 가능).

---

### 3.3 사용자 확인 및 투명성 (Explainability)

- **배경색**: AI가 자동 수정한 셀은 **Light Yellow (예: #FFFF99)**.
- **메모(Comment)**: 해당 셀에 AI가 선택한 **근거** 기록 (예: "작년 보고서 85% 일치", "Smelter Look-up CID 일치 + 명칭 유사도 0.92").
- **변경 이력**: 별도 시트 또는 로그로 "AI Change Log" 관리 (Timestamp, Sheet, Cell, Old/New, Confidence, Reason).

---

### 3.4 구버전 마이그레이션 (Legacy Data Support)

- **CMRT 6.4** 등 이전 버전 업로드 시 → **6.5 레이아웃**으로 매핑.
- **버전 감지**: Revision 시트 또는 시트 구조(Checker, Product List 등)로 판별.
- **마이그레이션 맵**: 시트별 행/열 매핑 규칙 정의 (Declaration 행 번호, Smelter List 헤더 행, 추가 컬럼 등).

---

## 4. Gemini의 구체적 역할

| 구간 | Gemini 역할 |
|------|-------------|
| **제련소 매칭** | 없음 (CID + 임베딩 유사도 + 임계값으로 결정) |
| **Declaration 답변** | 문서(RAG 결과) 기반으로 Q1~7에 대한 Yes/No/Unknown 답 + 근거 생성 |
| **메모(Explainability)** | 자동 입력된 셀에 넣을 "근거" 문구 생성 (선택) |
| **논리 검증 후** | 오류 시 수정 제안 생성 (선택) |
| **마이그레이션** | 없음 (규칙 기반 매핑) |

---

## 5. 기존 임베딩 재사용

- **Excel 필드 추출**에서 이미 `SemanticFieldMatcher`(또는 동일 임베딩 모델) 사용 중.
- **제련소 유사도 검색**도 동일 매처의 `rank_candidates(query, candidate_texts, top_k)` 로 처리.
- 장점: 모델·캐시·환경 설정 공유, 유지보수 일원화.

---

## 6. 기술 스택 (참고)

- **엑셀**: openpyxl, pandas, xlsxwriter  
- **임베딩/검색**: sentence-transformers, (선택) faiss-cpu / chromadb  
- **LLM**: google-generativeai (Gemini)  
- **유틸**: python-dotenv, pydantic, tqdm  

---

## 7. 아키텍처 (클래스 구조)

```
CMRTAgent
├── DataLoader          # load_smelter_lookup, load_declaration, detect_version
├── SmelterMatcher       # build_vector_db(또는 재사용), match_smelter, validate_dropdown
├── DeclarationValidator # validate_logic, auto_correct, generate_explanations
├── ExcelWriter          # write_smelter_list, write_declaration, mark_ai_cells, add_change_log
├── VersionMigrator      # detect_version, migrate
└── RAGPipeline          # embed_documents, query_documents, generate_answers (Gemini)
```

**메인 플로우**  
1. 버전 체크 → 필요 시 마이그레이션  
2. 소스 문서 임베딩(RAG)  
3. 제련소 매칭 (CID → 임베딩)  
4. Declaration 답변 생성 (RAG + Gemini)  
5. 논리 검증  
6. 엑셀 작성 + AI 셀 표시 + 메모/로그  

---

## 8. 주의사항

- **드롭다운 불일치**: AI가 넣은 값이 드롭다운 리스트에 없을 수 있음 → 사전 검증 필수.
- **엑셀 수식**: openpyxl 수정 시 수식 깨짐 가능 → 백업, data_only=False, 중요 시트 보호.
- **LLM 환각**: 제련소 이름은 **벡터 검색 결과만 사용**하고, LLM이 새 이름을 생성하지 않도록 제한.

---

## 9. 다음 단계 (구현 시)

1. Phase 1: SmelterMatcher (기존 SemanticFieldMatcher 활용)  
2. Phase 2: DeclarationValidator  
3. Phase 3: ExcelWriter (시각화 + 메모)  
4. Phase 4: VersionMigrator  
5. Phase 5: 통합 테스트 및 UI  

---

*문서 작성: 전략 설계 시점 기준. 구현 시 엑셀 실제 구조 재확인 권장.*
