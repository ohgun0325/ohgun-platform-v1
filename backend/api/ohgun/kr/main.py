"""FastAPI server for LangChain chatbot with pgvector."""

import sys
from pathlib import Path

# kr 모듈 루트를 Python 경로에 추가 (api.ohgun.kr.main 로드 시 import 해결용)
# 이 코드는 모든 import 전에 실행되어야 함
try:
    if __file__:
        project_root = Path(__file__).parent.absolute()
        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))
            print(f"[kr] module root added: {project_root}")
except NameError:
    # __file__이 없는 경우 (예: 인터랙티브 모드)
    pass

import asyncio
from contextlib import asynccontextmanager
from typing import Optional, Union

import psycopg2
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from api.v1.koica.koica_router import router as koica_router
from api.v1.detect.detect_router import router as detect_router
from domain.shared.router import router as shared_router
from api.v1.term.term_router import router as term_router
from api.v1.admin.user_router import router as user_router
from api.v1.evaluation.evaluation_router import router as evaluation_router
from api.v1.ocr.ocr_router import router as ocr_router
from core import (
    insert_sample_data,
    setup_pgvector,
    wait_for_db,
)
from artifacts.models.interfaces.base import BaseLLMModel
from artifacts.models.core.manager import ModelManager
from core.config import settings

try:
    from langchain_google_genai import ChatGoogleGenerativeAI
except ImportError:
    ChatGoogleGenerativeAI = None  # type: ignore


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database connection and chat model on startup."""
    print("🚀 FastAPI 서버 시작 중...")

    # Wait for database (동기 작업을 비동기로 실행)
    await asyncio.to_thread(wait_for_db)

    # Setup pgvector (동기 작업을 비동기로 실행)
    db_connection, embedding_dimension = await asyncio.to_thread(setup_pgvector)
    print(f"✅ 데이터베이스 연결 완료 (임베딩 차원: {embedding_dimension})")

    # Insert sample data if table is empty (동기 작업을 비동기로 실행)
    def check_and_insert_data():
        cur = db_connection.cursor()
        cur.execute("SELECT COUNT(*) FROM langchain_documents")
        count = cur.fetchone()[0]

        if count == 0:
            print("📚 샘플 데이터 삽입 중...")
            insert_sample_data(db_connection, embedding_dimension)
        else:
            print(f"✅ 기존 문서 {count}개 발견")

    await asyncio.to_thread(check_and_insert_data)

    # Initialize QLoRA chat service or fallback to original model
    qlora_service = None
    chat_model: Optional[Union[BaseLLMModel, ChatGoogleGenerativeAI]] = None

    # GPU 감지 정보 출력
    import torch
    cuda_available = torch.cuda.is_available()
    print("=" * 60)
    print("🔍 GPU 환경 확인")
    print("=" * 60)
    print(f"CUDA 사용 가능: {cuda_available}")
    if cuda_available:
        print(f"CUDA 버전: {torch.version.cuda}")
        print(f"GPU 개수: {torch.cuda.device_count()}")
        for i in range(torch.cuda.device_count()):
            print(f"  GPU {i}: {torch.cuda.get_device_name(i)}")
            props = torch.cuda.get_device_properties(i)
            print(f"    메모리: {props.total_memory / 1024**3:.2f} GB")
            print(f"    계산 능력: {props.major}.{props.minor}")
    else:
        print("⚠️  CUDA를 사용할 수 없습니다.")
        print("   GPU를 사용하려면:")
        print("   1. NVIDIA 드라이버 설치 확인")
        print("   2. Docker에서 GPU 지원 확인 (nvidia-docker)")
        print("   3. docker-compose.yml의 GPU 설정 확인")
    print(f"설정된 device_map: {settings.qlora_device_map}")
    print(f"설정된 MODEL_DEVICE: {settings.model_device}")
    print("=" * 60)
    print()

    if settings.use_qlora:
        # QLoRA 모델 사용
        try:
            from domain.koica.services.chat_service import QLoRAChatService

            print("📦 QLoRA 서비스 초기화 중... (시간이 걸릴 수 있습니다)")

            def init_qlora_service():
                # device_map이 "cpu"가 아니고 CUDA가 사용 가능하면 GPU 사용
                device_map = settings.qlora_device_map
                if device_map == "cpu":
                    print("⚠️  device_map이 'cpu'로 설정되어 있습니다. GPU를 사용하려면 'auto'로 변경하세요.")
                elif not cuda_available:
                    print("⚠️  CUDA를 사용할 수 없어 CPU로 실행됩니다.")
                    device_map = "cpu"
                else:
                    print(f"✅ GPU 사용: device_map='{device_map}'")

                service = QLoRAChatService(
                    model_name=settings.qlora_model_name,
                    output_dir=settings.qlora_output_dir,
                    use_4bit=settings.qlora_use_4bit,
                    bnb_4bit_compute_dtype=settings.qlora_bnb_4bit_compute_dtype,
                    bnb_4bit_quant_type=settings.qlora_bnb_4bit_quant_type,
                    bnb_4bit_use_double_quant=settings.qlora_bnb_4bit_use_double_quant,
                    device_map=device_map,
                )
                service.load_model()
                return service

            # 타임아웃 설정 (5분)
            try:
                qlora_service = await asyncio.wait_for(
                    asyncio.to_thread(init_qlora_service),
                    timeout=300.0
                )
                print("✅ QLoRA 채팅 서비스 로드 완료!")
            except asyncio.TimeoutError:
                print("⚠️  QLoRA 서비스 로드 타임아웃 (5분 초과)")
                print("   Fallback: 기존 모델 로딩 시도...")
                settings.use_qlora = False
                qlora_service = None
        except KeyboardInterrupt:
            print("\n⚠️  사용자가 QLoRA 로딩을 중단했습니다.")
            print("   Fallback: 기존 모델 로딩 시도...")
            settings.use_qlora = False
            qlora_service = None
        except Exception as e:
            print(f"⚠️  QLoRA 서비스 로드 중 오류: {str(e)}")
            print("   Fallback: 기존 모델 로딩 시도...")
            settings.use_qlora = False
            qlora_service = None

    if not settings.use_qlora or qlora_service is None:
        # 기존 모델 로딩 (QLoRA가 비활성화되었거나 로드 실패한 경우)
        # Try to load local model (Exaone) first (동기 작업을 비동기로 실행)
        if settings.default_chat_model:
            try:
                def load_local_model():
                    import os

                    # device 설정 확인 및 변환
                    device = settings.model_device
                    print(f"🔧 [Exaone 모델] 초기 MODEL_DEVICE 설정: {device}")

                    # CUDA가 사용 가능하고 device가 "cpu"가 아니면 GPU 사용
                    if torch.cuda.is_available():
                        if device == "cpu":
                            print(f"⚠️  MODEL_DEVICE가 'cpu'로 설정되어 있지만, CUDA가 사용 가능합니다.")
                            print(f"   GPU를 사용하도록 자동 변경합니다.")
                            device = "cuda"
                        elif device == "auto":
                            device = "cuda"
                        # device가 이미 "cuda"이면 그대로 사용
                    else:
                        if device != "cpu":
                            print(f"⚠️  CUDA를 사용할 수 없어 CPU로 변경합니다.")
                            device = "cpu"

                    print(f"🔧 [Exaone 모델] 최종 디바이스 설정: {device}")
                    print(f"🔧 [Exaone 모델] CUDA 사용 가능: {torch.cuda.is_available()}")

                    # ModelManager가 환경 변수를 읽을 수 있도록 설정
                    original_device_env = os.environ.get("MODEL_DEVICE")
                    os.environ["MODEL_DEVICE"] = device
                    print(f"🔧 [Exaone 모델] 환경 변수 MODEL_DEVICE={device}로 설정")

                    try:
                        manager = ModelManager()
                        # ModelManager에 device 파라미터 전달 시도
                        try:
                            # device 파라미터를 지원하는 경우
                            model = manager.get_chat_model(settings.default_chat_model, device=device)
                            if model:
                                print(f"✅ [Exaone 모델] {device.upper()}로 모델 로드 성공 (device 파라미터 사용)")
                            return model
                        except TypeError:
                            # device 파라미터를 지원하지 않는 경우, 환경 변수 사용
                            print(f"⚠️  ModelManager가 device 파라미터를 지원하지 않습니다.")
                            print(f"   환경 변수 MODEL_DEVICE={device}를 사용합니다.")
                            model = manager.get_chat_model(settings.default_chat_model)
                            if model:
                                print(f"✅ [Exaone 모델] 환경 변수를 통해 {device.upper()}로 모델 로드 시도")
                            return model
                    finally:
                        # 원래 환경 변수 값 복원
                        if original_device_env is not None:
                            os.environ["MODEL_DEVICE"] = original_device_env
                        elif "MODEL_DEVICE" in os.environ:
                            del os.environ["MODEL_DEVICE"]

                chat_model = await asyncio.to_thread(load_local_model)
                if chat_model:
                    print(f"✅ 로컬 모델 '{settings.default_chat_model}' 로드 완료!")
                else:
                    print(f"⚠️  로컬 모델 '{settings.default_chat_model}' 로드 실패")
            except Exception as e2:
                print(f"⚠️  로컬 모델 로드 중 오류: {str(e2)[:100]}")

        # Fallback to Gemini API if local model is not available
        print(f"🔍 Gemini API 로드 시도 - gemini_api_key 설정 여부: {settings.gemini_api_key is not None}")
        if chat_model is None and settings.gemini_api_key:
            print(f"🔑 Gemini API 키 길이: {len(settings.gemini_api_key)} (처음 10자: {settings.gemini_api_key[:10]}...)")
            try:
                def load_gemini_model():
                    from core import get_chat_model
                    return get_chat_model()

                gemini_model = await asyncio.to_thread(load_gemini_model)
                if gemini_model:
                    chat_model = gemini_model
                    print("✅ Gemini API 연결 확인 완료!")
                else:
                    print("⚠️  Gemini API를 사용할 수 없습니다. (get_chat_model()이 None 반환)")
            except Exception as e2:
                print(f"⚠️  Gemini API 로드 중 오류: {str(e2)[:200]}")
                import traceback
                traceback.print_exc()
        elif chat_model is None:
            print(f"⚠️  Gemini API 키가 설정되지 않았습니다. settings.gemini_api_key = {settings.gemini_api_key}")

        if chat_model is None:
            print("⚠️  사용 가능한 채팅 모델이 없습니다. 검색 기능만 사용 가능합니다.")

        app.state.chat_model = chat_model
    else:
        # QLoRA를 사용할 때는 chat_model을 None으로 설정 (GPU 메모리 절약)
        app.state.chat_model = None

    # Build LangGraph for complex queries (if chat_model is available)
    rag_graph = None
    if chat_model and not settings.use_qlora:
        try:
            from domain.koica.orchestrators.rag_orchestrator import build_rag_graph

            print("🔧 LangGraph 빌드 중...")
            rag_graph = await asyncio.to_thread(
                build_rag_graph,
                chat_model,
                db_connection,
                embedding_dimension
            )
            print("✅ LangGraph 빌드 완료!")
        except Exception as e:
            print(f"⚠️ LangGraph 빌드 실패: {str(e)[:200]}")
            import traceback
            traceback.print_exc()
            rag_graph = None

    # 인감도장/서명 검출용 YOLO 모델 로드 (1회)
    stamp_detector = None
    try:
        from domain.detect.services.stamp_detector import StampDetector
        _project_root = Path(__file__).resolve().parent.parent
        model_path = Path(settings.yolo_model_path)
        if not model_path.is_absolute():
            model_path = (_project_root / model_path).resolve()
        if model_path.exists():
            detector = StampDetector(
                model_path=str(model_path),
                conf_thres=settings.conf_thres,
            )
            await asyncio.to_thread(detector.load)
            stamp_detector = detector
            print("✅ 인감도장/서명 검출 모델(YOLO) 로드 완료")
        else:
            print(f"⚠️ YOLO 모델 없음 (경로: {model_path}). /api/v1/detect 비활성.")
            print(f"   → 학습 후 복사: runs/detect/stamp_detector/weights/best.pt → models/stamp_detector/best.pt")
    except Exception as e:
        print(f"⚠️ YOLO 모델 로드 실패: {e}. /api/v1/detect 비활성.")

    # Store in app state
    app.state.db_connection = db_connection
    app.state.embedding_dimension = embedding_dimension
    app.state.qlora_service = qlora_service
    app.state.rag_graph = rag_graph
    app.state.stamp_detector = stamp_detector

    print("✅ FastAPI 서버 준비 완료!")

    yield

    # Cleanup on shutdown (동기 작업을 비동기로 실행)
    qlora_service = getattr(app.state, "qlora_service", None)
    if qlora_service:
        await asyncio.to_thread(qlora_service.unload_model)
        print("👋 QLoRA 서비스 언로드 완료")

    if db_connection:
        await asyncio.to_thread(db_connection.close)
        print("👋 데이터베이스 연결 종료")


# Create FastAPI app
app = FastAPI(
    title=settings.app_title,
    description=settings.app_description,
    version=settings.app_version,
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=settings.cors_allow_methods,
    allow_headers=settings.cors_allow_headers,
)

# Include routers
app.include_router(shared_router)  # health, search
app.include_router(koica_router)  # koica chat (RAG)
app.include_router(detect_router, prefix="/api/v1")  # 인감도장/서명 검출
app.include_router(term_router)  # terms
app.include_router(user_router)  # admin user (rule-based / policy-based)
app.include_router(evaluation_router, prefix="/api/v1")  # RfP 평가 시스템
app.include_router(ocr_router, prefix="/api/v1")  # 글자 인식 OCR


@app.get("/", response_class=HTMLResponse)
async def read_root():
    """Serve the main HTML page."""
    try:
        with open("static/index.html", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return """
        <html>
            <head><title>LangChain Chatbot</title></head>
            <body>
                <h1>LangChain Chatbot API</h1>
                <p>API 문서: <a href="/docs">/docs</a></p>
                <p>프론트엔드: <a href="http://localhost:3000">Next.js 프론트엔드</a></p>
            </body>
        </html>
        """


def test_config_and_database():
    """Test config and database connection."""
    print("=" * 60)
    print("🧪 Config 및 Neon DB 연결 테스트 시작")
    print("=" * 60)

    # 1. Config 로드 테스트
    print("\n[1단계] Config 설정 확인")
    print("-" * 60)
    try:
        from core.config import settings

        print(f"✅ Config 모듈 로드 성공")
        print(f"   - App Title: {settings.app_title}")
        print(f"   - App Version: {settings.app_version}")
        print(f"   - Database Host: {settings.postgres_host}")
        print(f"   - Database Port: {settings.postgres_port}")
        print(f"   - Database Name: {settings.postgres_db}")
        print(f"   - Database User: {settings.postgres_user}")
        print(f"   - SSL Mode: {settings.postgres_sslmode}")
        print(f"   - DATABASE_URL 설정 여부: {'✅ 설정됨' if settings.database_url else '❌ 미설정 (개별 파라미터 사용)'}")

        # Database URL 생성 테스트
        db_url = settings.get_database_url()
        # 비밀번호 마스킹
        if "@" in db_url:
            masked_url = db_url.split("@")[0].split(":")[0] + ":***@" + "@".join(db_url.split("@")[1:])
        else:
            masked_url = db_url
        print(f"   - 생성된 DATABASE_URL: {masked_url}")

    except Exception as e:
        print(f"❌ Config 로드 실패: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

    # 2. Database 연결 테스트
    print("\n[2단계] Neon PostgreSQL 연결 테스트")
    print("-" * 60)
    try:
        import psycopg2
        from core.database import get_db_connection

        print("🔄 데이터베이스 연결 시도 중...")
        conn = get_db_connection(register_vector_extension=False)

        # 연결 정보 확인
        cur = conn.cursor()
        cur.execute("SELECT version();")
        version = cur.fetchone()[0]
        print(f"✅ 데이터베이스 연결 성공!")
        print(f"   - PostgreSQL 버전: {version.split(',')[0]}")

        # 현재 데이터베이스 확인
        cur.execute("SELECT current_database();")
        current_db = cur.fetchone()[0]
        print(f"   - 현재 데이터베이스: {current_db}")

        # 사용자 확인
        cur.execute("SELECT current_user;")
        current_user = cur.fetchone()[0]
        print(f"   - 현재 사용자: {current_user}")

        # 테이블 목록 확인
        cur.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)
        tables = cur.fetchall()
        if tables:
            print(f"   - 공개 스키마 테이블 수: {len(tables)}개")
            print(f"   - 테이블 목록: {', '.join([t[0] for t in tables[:5]])}{'...' if len(tables) > 5 else ''}")
        else:
            print(f"   - 공개 스키마 테이블: 없음")

        # pgvector 확장 확인
        cur.execute("""
            SELECT EXISTS(
                SELECT 1 FROM pg_extension WHERE extname = 'vector'
            );
        """)
        has_vector = cur.fetchone()[0]
        print(f"   - pgvector 확장: {'✅ 설치됨' if has_vector else '❌ 미설정'}")

        cur.close()
        conn.close()
        print("✅ 데이터베이스 연결 테스트 완료!")

    except psycopg2.OperationalError as e:
        print(f"❌ 데이터베이스 연결 실패 (OperationalError)")
        print(f"   오류 메시지: {str(e)}")
        print(f"\n   가능한 원인:")
        print(f"   1. 데이터베이스 호스트/포트가 잘못되었습니다")
        print(f"   2. 네트워크 연결 문제가 있습니다")
        print(f"   3. SSL 설정이 잘못되었습니다")
        return False
    except psycopg2.Error as e:
        print(f"❌ 데이터베이스 오류 발생")
        print(f"   오류 메시지: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"❌ 예상치 못한 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

    # 3. Config와 Database 연동 테스트
    print("\n[3단계] Config와 Database 연동 테스트")
    print("-" * 60)
    try:
        # wait_for_db 함수 테스트
        from core.database import wait_for_db

        print("🔄 wait_for_db() 함수 테스트...")
        wait_for_db(max_retries=3)
        print("✅ wait_for_db() 함수 정상 작동!")

    except Exception as e:
        print(f"❌ wait_for_db() 테스트 실패: {str(e)}")
        return False

    print("\n" + "=" * 60)
    print("✅ 모든 테스트 통과! Config와 Neon DB 연결 정상")
    print("=" * 60)
    return True


if __name__ == "__main__":
    import sys

    # 테스트 모드 확인 (--test 플래그)
    if "--test" in sys.argv or "-t" in sys.argv:
        # 테스트만 실행
        success = test_config_and_database()
        sys.exit(0 if success else 1)
    else:
        # 테스트 실행 후 서버 시작
        print("🚀 FastAPI 서버 시작 전 Config 및 DB 연결 테스트 실행...")
        test_success = test_config_and_database()

        if not test_success:
            print("\n⚠️  테스트 실패했지만 서버는 계속 시작합니다...")
            print("   (서버 시작 시 자동으로 재시도합니다)\n")

        import uvicorn
        uvicorn.run(
            "api.ohgun.kr.main:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
        )
