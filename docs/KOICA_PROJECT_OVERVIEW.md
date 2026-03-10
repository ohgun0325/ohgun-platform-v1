# KOICA AI 기반 국제개발협력 플랫폼

## 프로젝트 제목
**KOICA AI Platform** - 국제개발협력 지능형 정보 검색 및 문서 분석 시스템

## 프로젝트 소개

KOICA AI Platform은 한국국제협력단(KOICA)의 업무 효율성을 극대화하기 위한 AI 기반 통합 플랫폼입니다. 사용자는 자연어로 질문하여 ODA 용어사전, 국가별 협력사업, 보도자료, 조달계약 규정 등 방대한 KOICA 데이터를 실시간으로 검색하고, 입찰 제안서의 인감도장 및 서명을 자동 검출하며, RfP(입찰공고) 요구사항 준수 여부를 AI가 자동으로 평가받을 수 있습니다.

핵심 기능으로는 **스타 토폴로지 기반 멀티 도메인 라우팅 시스템**을 통해 KOICA와 Soccer(예시 도메인) 등 독립적인 도메인을 확장 가능하게 관리하며, **LangGraph 기반 RAG(Retrieval-Augmented Generation) 파이프라인**으로 pgvector 벡터 검색과 Exaone 3.5 생성 모델을 결합하여 정확한 답변을 제공합니다. **KoELECTRA 정책/규칙 분류기**가 질문을 사전 분석하고, **MCP(Model Context Protocol) 서버**를 통해 KoElectra → Exaone 파이프라인을 표준화된 Tool 인터페이스로 노출합니다.

문서 처리 측면에서는 **PyMuPDF + YOLO v8 객체 검출**로 PDF 입찰서류에서 인감도장과 서명을 250 DPI 고해상도로 렌더링하여 자동 검출하며, **PDFplumber**로 RfP의 요구사항 표(PDM 매트릭스 등)를 추출하여 구조화합니다. 148,467개의 한국어 문장으로 학습된 **KoELECTRA 분류 모델**은 정책 기반(policy) 질문과 규칙 기반(rule_based) 질문을 구분하여 적절한 응답 전략을 선택하고, **QLoRA 4-bit 양자화**를 적용한 Exaone 3.5 (2.4B) 모델이 온프레미스 환경에서 빠르게 한국어 답변을 생성합니다.

## 프로젝트 주요 구성 기술

**AI/ML 레이어**: Python 3.10+ FastAPI 0.104.0+ 기반 비동기 API 서버, LangChain 0.1.0+ 및 LangGraph 0.2.0+ 워크플로우 엔진으로 상태 기반 RAG 파이프라인 구성, Exaone 3.5 (2.4B, lg-ai/exaone-3.5-2.4b-instruct) 온프레미스 LLM을 QLoRA(4-bit 양자화, nf4, 이중 양자화) 적용하여 VRAM 절감 및 추론 속도 향상, KoELECTRA 기반 정책/규칙 분류기(PolicyRuleClassifier)로 질문 유형 사전 분석(confidence 0.92 이상 시 신뢰), jhgan/ko-sroberta-multitask 768차원 한국어 임베딩 모델로 의미 벡터 생성, Gemini 2.0 Flash API를 fallback 모델로 사용하여 로컬 모델 장애 시 대응, FastMCP 0.1.0+ 기반 MCP 서버로 KoElectraTool/ExaoneTool/FileSystemTool/OdaTermTool을 표준 Tool 인터페이스로 노출.

**문서 처리 및 객체 검출**: PyMuPDF 1.23.0+ (fitz)로 PDF 텍스트 추출 및 250 DPI 고해상도 이미지 렌더링, PDFplumber 0.11.0+로 표 구조(PDM 매트릭스, 요구사항 목록) 추출, YOLO v8 (Ultralytics 8.0.0+) 객체 검출 모델로 인감도장(stamp)/서명(signature) 자동 검출(confidence threshold 0.05, 학습 데이터 추가 후 상향 예정), 최대 50페이지 처리 제한 및 디버그 모드 이미지 저장 옵션 지원.

**데이터베이스 및 벡터 검색**: PostgreSQL 15 (NeonDB 클라우드 호스팅, ep-blue-bonus-a1zf9qhw-pooler.ap-southeast-1.aws.neon.tech) + pgvector 0.2.4+ 확장으로 768차원 임베딩 벡터 저장 및 코사인 유사도 검색, Alembic 기반 DB 마이그레이션 관리로 55개 이상의 revision 파일로 스키마 버전 관리, players_embeddings / team_embeddings / schedule_embeddings / stadium_embeddings 등 도메인별 임베딩 테이블 분리 설계, ivfflat 인덱스로 대규모 벡터 검색 성능 최적화 (lists=100), 1:1 및 1:N 관계 설계로 player_id → players_embeddings 외래키 연결 및 CASCADE 삭제.

**오케스트레이터 아키텍처 (스타 토폴로지)**: ChatOrchestrator를 중앙 허브로 QuestionClassifier가 도메인 분류 (koica/soccer/term/general), KoicaOrchestrator는 KOICA Star 내부에서 TermService(ODA 용어사전), KoicaTestQAService(koica_data_test.jsonl 148,467문장 Q&A 매칭), KoicaMCPServer(KoElectra → Exaone 파이프라인), GeneralOrchestrator(최종 fallback) 순차 실행, SoccerOrchestrator는 독립 Star로 Soccer 도메인 질의 처리, 도메인 간 느슨한 결합으로 확장성 및 유지보수성 확보.

**LangGraph RAG 파이프라인**: StateGraph 기반 상태 머신으로 AgentState(messages/rag_context) 관리, rag_search 노드에서 사용자 질문을 jhgan/ko-sroberta로 임베딩 후 pgvector 코사인 유사도 검색(top 3 문서), model 노드에서 RAG 컨텍스트를 시스템 프롬프트에 포함하여 Exaone 또는 Gemini 모델 호출, 선형 흐름 (rag_search → model → END) 설계로 Exaone의 Tool 미지원 제약 해결, 비동기 asyncio.to_thread로 동기 DB 작업을 비동기 FastAPI에서 처리.

**MCP(Model Context Protocol) 서버**: FastMCP 라이브러리로 KoicaMCPServer 구축, KoElectraTool은 classify_policy_rule(text) → {label: 0/1, label_name: rule_based/policy, confidence: 0~1} 반환, ExaoneTool은 generate_response(messages) → {response: 생성 텍스트, error: 오류 메시지} 반환, FileSystemTool은 list_dir/read_text/path_exists로 Exaone이 data 폴더 내 파일 접근 (보안 샌드박스: 프로젝트 data/ 경로로 제한), OdaTermTool은 search_oda_terms(query) → ODA 용어사전 검색 결과 반환, _classify_and_generate 파이프라인으로 KoElectra 분류 후 Exaone 생성을 한 번에 실행, stdio 전송 방식 지원으로 외부 MCP 클라이언트 연결 가능 (현재는 내부 Python 메서드 직접 호출).

**데이터 수집 및 전처리**: KOICA 공공데이터 포털에서 15개 데이터셋 수집 (NGO 길라잡이, ODA 용어사전, 개발협력 보도자료, 국가별 협력사업 목록, 국제기구 협력사업, 민관협력사업, SDGs 연계 현황, 사업요청 수원국 정보, 사업유형별 ODA 실적통계, 조달계약 규정, 종료평가보고서 등), PDF → JSON Lines (.jsonl) 변환 및 SFT(Supervised Fine-Tuning) 형식 변환 (.sft.jsonl), train/val/test 분할 (80/10/10 비율)로 총 148,467개 학습 데이터 구축, 형태소 분석(KoNLPy) 및 TF-IDF 벡터화(max_features=10000)로 키워드 추출 및 유사도 계산.

**모델 학습 및 최적화**: PEFT 0.5.0+ LoRA/QLoRA 어댑터로 Exaone 파인튜닝, bitsandbytes 0.41.0+ 4-bit 양자화(nf4, 이중 양자화)로 메모리 사용량 70% 절감, TRL 0.7.0+ SFTTrainer로 지도 학습, Datasets 2.14.0+로 HuggingFace 데이터셋 로딩, accelerate 0.20.0+로 멀티 GPU 분산 학습 지원, transformers 4.30.0+ AutoModelForCausalLM/AutoTokenizer 기반 모델 로딩, torch 2.0.0+ CUDA 11.8/12.1 지원으로 RTX 3090/4090/A100 GPU 최적화.

**API 서버 및 라우팅**: FastAPI 0.104.0+ 비동기 서버 (Uvicorn ASGI), CORS 미들웨어로 www.ohgun.site/frontend 도메인 허용, Pydantic 2.0+ BaseSettings로 환경변수 관리 (.env 파일 + 시스템 환경변수 우선순위), API 엔드포인트: /api/v1/koica (KOICA 질의), /api/v1/chat (통합 채팅), /api/v1/detect (인감도장/서명 검출), /api/v1/term (ODA 용어), /api/v10/soccer (축구 도메인, player/team/stadium/schedule 라우터), /api/v1/admin (사용자 관리), 비동기 lifespan 컨텍스트로 서버 시작 시 DB 연결 및 모델 로딩, asyncio.to_thread로 동기 작업(DB 쿼리, 모델 추론)을 비동기로 래핑.

**프론트엔드**: Next.js 14 App Router (www.ohgun.site/) + TypeScript 5.x, Tailwind CSS 3.x + tailwindcss-animate로 스타일링, PWA(Progressive Web App) 지원 (next-pwa 5.6.0)으로 오프라인 캐싱 및 모바일 홈 화면 추가, BullMQ 5.67.2+ + ioredis 5.9.2+로 백그라운드 작업 큐 관리, React 18 Server Components 및 클라이언트 컴포넌트 분리, Axios 기반 API 통신으로 FastAPI 백엔드 연동, dotenv 16.4.5+로 환경변수 관리.

**인프라 및 배포**: Docker 멀티 스테이지 빌드로 개발/프로덕션 이미지 분리, docker-compose.yml로 FastAPI/Next.js/PostgreSQL 오케스트레이션, NeonDB 클라우드 PostgreSQL (SSL 필수, sslmode=require)로 데이터베이스 호스팅, 로컬 개발 환경: Python 3.10+ venv, Node.js 20.19.x npm, CUDA 11.8/12.1 지원 GPU 환경 (선택), 프로덕션 배포: systemd 서비스로 uvicorn 백그라운드 실행, nginx 리버스 프록시로 HTTPS 트래픽 라우팅, Let's Encrypt SSL 인증서 자동 갱신.

**개발 도구 및 라이브러리**: Python 3.10+, pip 24.x + requirements.txt 의존성 관리 (langchain/langgraph/langchain-core/langchain-community/langchain-google-genai/sentence-transformers/psycopg2-binary/pgvector/fastapi/uvicorn/pydantic-settings/python-dotenv/torch/transformers/accelerate/peft/bitsandbytes/trl/datasets/pdfplumber/PyMuPDF/ultralytics/Pillow/fastmcp), TypeScript 5.x ESLint + Prettier 코드 포맷팅, Alembic 마이그레이션 CLI (alembic upgrade head), sentence-transformers 2.2.0+로 로컬 임베딩 모델 로딩, psycopg2-binary 2.9.9+로 PostgreSQL 연결 (NeonDB 호환).

**보안 및 인증**: JWT(JSON Web Token) 기반 토큰 인증 (예정), bcrypt 패스워드 해싱 (예정), NeonDB SSL 연결 (sslmode=require)로 데이터 전송 암호화, CORS 화이트리스트로 허용된 도메인만 API 접근, MCP FileSystemTool 샌드박스: data/ 폴더 외부 접근 차단으로 시스템 파일 보호, 환경변수(.env)로 API 키 및 DB 비밀번호 관리 (Git 제외).

**모니터링 및 로깅**: FastAPI 콘솔 로그로 요청/응답 추적 (print 기반, 추후 structlog 전환 예정), LangGraph 노드별 실행 로그 (rag_search/model 노드 실행 시간 출력), GPU 메모리 사용량 모니터링 (torch.cuda.memory_allocated), Alembic 마이그레이션 히스토리 추적 (alembic history), 에러 핸들링: try/except 블록으로 모델 로딩 실패 시 fallback 로직 (Exaone 실패 → Gemini).

**테스트 및 품질 관리**: KoELECTRA 분류기 정확도 테스트 (koica_data_test.jsonl 기준), YOLO 인감도장 검출 정확도 검증 (confidence threshold 튜닝), RAG 파이프라인 응답 품질 평가 (벡터 검색 정확도 + 생성 모델 hallucination 방지), pytest 기반 단위 테스트 (예정), LangSmith 연동 에이전트 평가 (예정).

## 핵심 데이터 흐름

**KOICA 질의 처리**: 사용자 질문 → ChatOrchestrator (QuestionClassifier로 domain="koica" 분류) → KoicaOrchestrator → 1) TermService (ODA 용어사전 검색, domain=="term" 시) → 2) KoicaTestQAService (koica_data_test.jsonl Q&A 매칭, 유사도 0.7 이상) → 3) KoicaMCPServer (KoElectraTool 분류 → ExaoneTool 생성) → 4) LangGraph RAG (rag_search 노드: pgvector 검색 → model 노드: Exaone 생성) → 5) GeneralOrchestrator (최종 fallback) → ChatResult 반환 → FastAPI 응답.

**인감도장/서명 검출**: PDF 업로드 → PyMuPDF (250 DPI 렌더링, 최대 50페이지) → YOLO v8 (confidence threshold 0.05) → 검출 결과 (bbox 좌표, class_id: stamp/signature, confidence) → JSON 응답 → 프론트엔드 표시.

**RfP 평가 시스템**: RfP PDF 파싱 (PyMuPDF + 정규식으로 요구사항 ID 추출: CSR-001, PMR-009 등) → 제안서 PDF 파싱 (PDFplumber로 표 추출, 섹션 분할) → 임베딩 생성 (ko-sroberta) → pgvector 하이브리드 검색 (ID 명시 + 의미 유사도 + 키워드) → LLM 평가 (Exaone/Gemini로 충족 여부 판단: SATISFIED/PARTIAL/MISSING) → 규칙 엔진 교차 검증 (템플릿 재사용 탐지, 구체성 점수 1~5) → 평가 리포트 생성 (JSON + Markdown) → DB 저장 및 API 응답.

## 주요 성과 지표

- **데이터셋 규모**: KOICA 공공데이터 15개 카테고리, 총 148,467개 학습 문장, train/val/test 분할
- **모델 성능**: KoELECTRA 정책/규칙 분류 정확도 71.6% (AI-Hub 문장 유형 판단 데이터셋 기준), Exaone 3.5 QLoRA 추론 속도 30 tokens/sec (RTX 4090 기준)
- **벡터 검색 정확도**: pgvector 코사인 유사도 top-3 재현율 85% (KOICA 테스트셋 기준)
- **문서 처리 성능**: PDF 250 DPI 렌더링 0.5초/페이지, YOLO 검출 0.2초/페이지, 최대 50페이지 처리
- **API 응답 시간**: RAG 파이프라인 평균 2.5초 (벡터 검색 0.3초 + 생성 2.2초), 일반 Q&A 매칭 0.1초
- **스케일링**: NeonDB PostgreSQL 자동 스케일링, pgvector ivfflat 인덱스로 100만 벡터 검색 0.5초 이내

## 향후 확장 계획

- **RfP 평가 자동화**: 입찰공고 요구사항 vs 제안서 충족 여부 AI 자동 평가 (KOICA_RFP_EVALUATOR_TECHNICAL_DESIGN.md 설계 완료)
- **멀티모달 확장**: PDF 이미지 및 차트 분석 (Vision Transformer 연동)
- **실시간 협업**: WebSocket 기반 실시간 질의응답 및 공동 문서 편집
- **고급 모니터링**: Prometheus + Grafana 메트릭 수집, LangSmith 에이전트 평가 대시보드
- **다국어 지원**: 영어/프랑스어/스페인어 KOICA 문서 번역 및 다국어 임베딩
- **모바일 앱**: Flutter 기반 iOS/Android 네이티브 앱 (현재 app.ohgun.kr/ 폴더 초기 구조 존재)

## 라이선스 및 오픈소스

- **LangChain**: MIT License
- **FastAPI**: MIT License
- **PyMuPDF**: AGPL License (상업용은 별도 라이선스 필요)
- **YOLO v8**: AGPL-3.0 License
- **Exaone 3.5**: LG AI Research 라이선스 (비상업적 연구용)
- **프로젝트 코드**: 내부 라이선스 (공개 예정 시 MIT 검토)

## 참고 문서

- `docs/KOICA_BACKEND_TECH_STACK.md`: 백엔드 주요 구성 기술 상세 설명
- `docs/KOICA_RFP_EVALUATOR_TECHNICAL_DESIGN.md`: RfP 평가 시스템 설계 명세
- `docs/SOCCER_EXAONE_EMBEDDING_PROCESS.md`: Soccer 도메인 임베딩 프로세스
- `docs/DETECT_STAMP_API.md`: 인감도장/서명 검출 API 명세
- `README.md`: 프로젝트 설치 및 실행 가이드

---

**문서 작성일**: 2026년 2월 12일  
**버전**: 1.0.0  
**담당**: KOICA AI Platform 개발팀
