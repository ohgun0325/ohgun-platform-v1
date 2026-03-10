"""LangChain Hello World with pgvector integration example."""

import os
import time
from typing import List, Optional

import psycopg2
from pgvector.psycopg2 import register_vector

try:
    from langchain_google_genai import (
        ChatGoogleGenerativeAI,
        GoogleGenerativeAIEmbeddings,
    )
    from langchain_core.messages import HumanMessage, SystemMessage
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False


def wait_for_db(max_retries: int = 30) -> None:
    """Wait for PostgreSQL database to be ready.

    Args:
        max_retries: Maximum number of connection attempts.
    """
    print("🔄 데이터베이스 연결 대기 중...")

    for attempt in range(max_retries):
        try:
            conn = psycopg2.connect(
                host=os.getenv("POSTGRES_HOST", "pgvector"),
                port=os.getenv("POSTGRES_PORT", "5432"),
                user=os.getenv("POSTGRES_USER", "langchain"),
                password=os.getenv("POSTGRES_PASSWORD", "langchain_password"),
                database=os.getenv("POSTGRES_DB", "vectordb")
            )
            conn.close()
            print("✅ 데이터베이스 연결 성공!")
            return
        except psycopg2.OperationalError:
            if attempt < max_retries - 1:
                print(f"⏳ 재시도 {attempt + 1}/{max_retries}...")
                time.sleep(2)
            else:
                raise Exception("데이터베이스 연결 실패")


def test_gemini_api() -> int:
    """Test if Gemini API is available and return embedding dimension.

    Returns:
        Embedding dimension if API is available and working, otherwise 0.
    """
    if not GEMINI_AVAILABLE:
        return 0

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return 0

    try:
        embeddings_model = GoogleGenerativeAIEmbeddings(
            model="text-embedding-004",
            api_key=api_key,
        )
        # Test with a single word to check if API works and get dimension dynamically
        test_embedding = embeddings_model.embed_query("test")
        return len(test_embedding)
    except Exception:
        return 0


def get_embedding_dimension() -> int:
    """Get the embedding dimension based on Gemini API availability.

    Returns:
        Embedding dimension (Gemini embedding dim or 3 for dummy).
    """
    dim = test_gemini_api()
    if dim > 0:
        return dim
    return 3  # Dummy embedding dimension


def setup_pgvector() -> tuple[psycopg2.extensions.connection, int]:
    """Setup pgvector extension and create sample table.

    Returns:
        Tuple of (database connection object, embedding dimension).
    """
    conn = psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "pgvector"),
        port=os.getenv("POSTGRES_PORT", "5432"),
        user=os.getenv("POSTGRES_USER", "langchain"),
        password=os.getenv("POSTGRES_PASSWORD", "langchain_password"),
        database=os.getenv("POSTGRES_DB", "vectordb")
    )

    cur = conn.cursor()

    # Enable pgvector extension FIRST (before registering)
    cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
    conn.commit()

    # Register pgvector extension AFTER creating it
    register_vector(conn)

    # Get embedding dimension (test API first)
    embedding_dim = get_embedding_dimension()

    # Create sample table for embeddings
    cur.execute("DROP TABLE IF EXISTS langchain_documents")
    cur.execute(f"""
        CREATE TABLE langchain_documents (
            id SERIAL PRIMARY KEY,
            content TEXT,
            embedding VECTOR({embedding_dim})
        )
    """)

    conn.commit()
    print(f"✅ pgvector 확장 및 테이블 생성 완료! (임베딩 차원: {embedding_dim})")

    return conn, embedding_dim


def generate_embeddings(texts: List[str], dimension: int = 3) -> List[List[float]]:
    """Generate embeddings using Gemini or dummy embeddings.

    Args:
        texts: List of text strings to embed.
        dimension: Expected dimension for embeddings.

    Returns:
        List of embedding vectors.
    """
    api_key = os.getenv("GEMINI_API_KEY")

    if GEMINI_AVAILABLE and api_key:
        try:
            embeddings_model = GoogleGenerativeAIEmbeddings(
                model="text-embedding-004",
                api_key=api_key,
            )
            embeddings = embeddings_model.embed_documents(texts)
            print("🤖 Gemini API를 사용하여 임베딩 생성 완료!")
            return embeddings
        except Exception as e:
            error_msg = str(e)
            print(f"⚠️  임베딩 생성 오류: {error_msg[:100]}")
            print(f"   더미 임베딩을 사용합니다. (차원: {dimension})")
            # Fallback to dummy embeddings with correct dimension
            return generate_dummy_embeddings(len(texts), dimension)
    else:
        print(f"⚠️  GEMINI_API_KEY가 없어 더미 임베딩을 사용합니다. (차원: {dimension})")
        return generate_dummy_embeddings(len(texts), dimension)


def generate_dummy_embeddings(count: int, dimension: int) -> List[List[float]]:
    """Generate dummy embeddings with specified dimension.

    Args:
        count: Number of embeddings to generate.
        dimension: Dimension of each embedding.

    Returns:
        List of dummy embedding vectors.
    """
    embeddings = []
    for i in range(count):
        # Create a simple pattern: first few dimensions are 1.0, rest are 0.0
        embedding = [0.0] * dimension
        if dimension > 0:
            embedding[i % dimension] = 1.0
        embeddings.append(embedding)
    return embeddings


def insert_sample_data(conn: psycopg2.extensions.connection, dimension: int) -> None:
    """Insert sample documents with embeddings.

    Args:
        conn: Database connection object.
        dimension: Expected embedding dimension.
    """
    cur = conn.cursor()

    # Sample documents - 더 다양한 정보 제공
    sample_docs = [
        "LangChain is a framework for developing applications powered by language models. It provides tools for building AI applications with LLMs.",
        "pgvector is a PostgreSQL extension that enables vector similarity search. It allows you to store and query high-dimensional vectors efficiently.",
        "Vector databases store embeddings which are numerical representations of text, images, or other data. They enable semantic search and similarity matching.",
        "RAG (Retrieval Augmented Generation) combines information retrieval with language models to provide more accurate and context-aware responses.",
        "Embeddings are dense vector representations that capture semantic meaning. Similar concepts have similar embeddings in the vector space.",
        "LangChain supports multiple LLM providers including OpenAI, Anthropic, and open-source models. It provides a unified interface for working with different models.",
    ]

    # Generate embeddings with correct dimension
    embeddings = generate_embeddings(sample_docs, dimension)

    # Insert documents with embeddings
    for content, embedding in zip(sample_docs, embeddings):
        cur.execute(
            "INSERT INTO langchain_documents (content, embedding) VALUES (%s, %s::vector)",
            (content, embedding)
        )

    conn.commit()
    print(f"✅ {len(sample_docs)}개의 샘플 문서 삽입 완료!")


def query_similar_documents(
    conn: psycopg2.extensions.connection,
    query_embedding: List[float],
    limit: int = 3
) -> List[tuple]:
    """Query documents similar to the given embedding.

    Args:
        conn: Database connection object.
        query_embedding: Query vector for similarity search.
        limit: Maximum number of results to return.

    Returns:
        List of tuples (doc_id, content, distance).
    """
    cur = conn.cursor()

    # Find similar documents using cosine distance
    # Cast the parameter to vector type explicitly
    cur.execute(
        """
        SELECT id, content, embedding <=> %s::vector AS distance
        FROM langchain_documents
        ORDER BY distance
        LIMIT %s
        """,
        (query_embedding, limit)
    )

    results = cur.fetchall()
    return results


def chat_with_ai(
    conn: psycopg2.extensions.connection,
    user_input: str,
    dimension: int,
    chat_model: Optional["ChatGoogleGenerativeAI"] = None
) -> str:
    """Chat with AI using RAG (Retrieval Augmented Generation).

    Args:
        conn: Database connection object.
        user_input: User's question or message.
        dimension: Expected embedding dimension.
        chat_model: OpenAI chat model instance (None if API unavailable).

    Returns:
        AI's response as a string.
    """
    api_key = os.getenv("GEMINI_API_KEY")

    if not GEMINI_AVAILABLE or not api_key:
        # If chat_model is None, it means API is not available (quota exceeded, etc.)
        # Still try to search and return relevant documents
        print("🔍 관련 문서 검색 중...")
        query_embeddings = generate_embeddings([user_input], dimension)
        query_vector = query_embeddings[0]
        similar_docs = query_similar_documents(conn, query_vector, limit=3)

        if similar_docs:
            context = "\n".join([f"- {content}" for _, content, _ in similar_docs])
            return f"""⚠️ Gemini API를 사용할 수 없습니다 (키 누락 또는 연결 오류).

하지만 데이터베이스에서 관련 문서를 찾았습니다:

{context}

이 정보를 참고하시기 바랍니다."""
        else:
            return "⚠️ Gemini API를 사용할 수 없고, 관련 문서도 찾지 못했습니다."

    # If chat_model is None, API는 있지만 이전 테스트에서 실패한 경우
    if chat_model is None:
        print("⚠️ Gemini 챗 모델이 활성화되지 않았습니다. 검색 결과만 반환합니다.")
        print("🔍 관련 문서 검색 중...")
        query_embeddings = generate_embeddings([user_input], dimension)
        query_vector = query_embeddings[0]
        similar_docs = query_similar_documents(conn, query_vector, limit=3)

        if similar_docs:
            context = "\n".join([f"- {content}" for _, content, _ in similar_docs])
            return f"""🔎 다음은 검색된 관련 문서입니다:

{context}"""
        return "⚠️ 관련 문서를 찾지 못했습니다."

    # Generate embedding for user query
    print("🔍 관련 문서 검색 중...")
    query_embeddings = generate_embeddings([user_input], dimension)
    query_vector = query_embeddings[0]

    # Search for similar documents
    similar_docs = query_similar_documents(conn, query_vector, limit=3)

    # Build context from retrieved documents
    context = "\n".join([f"- {content}" for _, content, _ in similar_docs])

    # Create system message with context
    system_message = SystemMessage(content=f"""당신은 도움이 되는 AI 어시스턴트입니다.
다음은 데이터베이스에서 검색된 관련 문서입니다:

{context}

이 정보를 바탕으로 사용자의 질문에 답변해주세요.
관련 문서에 없는 정보에 대해서는 일반적인 지식을 바탕으로 답변할 수 있습니다.""")

    # Create user message
    human_message = HumanMessage(content=user_input)

    # Get AI response with error handling
    print("🤖 AI가 응답 생성 중...")
    try:
        response = chat_model.invoke([system_message, human_message])
        return response.content
    except Exception as e:
        error_msg = str(e)
        if "quota" in error_msg.lower() or "429" in error_msg or "insufficient_quota" in error_msg:
            # API 할당량 초과 시 검색된 문서 기반으로 간단한 응답 생성
            if similar_docs:
                return f"""⚠️ OpenAI API 할당량이 초과되어 AI 응답을 생성할 수 없습니다.

하지만 데이터베이스에서 관련 문서를 찾았습니다:

{context}

이 정보를 참고하시기 바랍니다. API 할당량을 확인하시려면 https://platform.openai.com/account/billing 을 방문하세요."""
            else:
                return "⚠️ OpenAI API 할당량이 초과되어 응답을 생성할 수 없습니다. 관련 문서도 찾지 못했습니다. API 할당량을 확인하시려면 https://platform.openai.com/account/billing 을 방문하세요."
        else:
            return f"❌ 오류 발생: {error_msg[:200]}"


def interactive_chat(conn: psycopg2.extensions.connection, dimension: int) -> None:
    """Start interactive chat session with AI.

    Args:
        conn: Database connection object.
        dimension: Expected embedding dimension.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not GEMINI_AVAILABLE or not api_key:
        print("⚠️  GEMINI_API_KEY 환경변수가 설정되지 않았거나, Gemini 라이브러리가 설치되지 않았습니다.")
        print("   `langchain-google-genai`를 설치하고 GEMINI_API_KEY를 설정하면 대화 기능을 사용할 수 있습니다.")
        return

    print("\n" + "=" * 60)
    print("💬 대화형 AI 챗봇 시작")
    print("=" * 60)
    print("💡 'quit', 'exit', '종료'를 입력하면 대화를 종료합니다.")
    print("=" * 60 + "\n")

    # Try to create chat model and test if it works
    chat_model: Optional[ChatGoogleGenerativeAI] = None
    try:
        chat_model = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            temperature=0.7,
            api_key=api_key,
        )
        # Test if API works
        _ = chat_model.invoke([HumanMessage(content="test")])
        print("✅ Gemini API 연결 확인 완료!\n")
    except Exception as e:
        error_msg = str(e)
        print(f"⚠️  Gemini API 연결 또는 호출 오류: {error_msg[:120]}")
        print("   검색 기능만 사용 가능합니다.\n")
        chat_model = None

    while True:
        try:
            user_input = input("👤 당신: ").strip()

            if not user_input:
                continue

            if user_input.lower() in ['quit', 'exit', '종료', 'q']:
                print("\n👋 대화를 종료합니다. 안녕히가세요!")
                break

            # Get AI response
            response = chat_with_ai(conn, user_input, dimension, chat_model)
            print(f"\n🤖 AI: {response}\n")
            print("-" * 60 + "\n")

        except KeyboardInterrupt:
            print("\n\n👋 대화를 종료합니다. 안녕히가세요!")
            break
        except Exception as e:
            print(f"\n❌ 오류 발생: {e}\n")
            print("-" * 60 + "\n")


def main() -> None:
    """Main function to demonstrate LangChain with pgvector."""
    print("=" * 60)
    print("🚀 LangChain + pgvector Hello World 예제")
    print("=" * 60)

    # Check Gemini API key
    gemini_key = os.getenv("GEMINI_API_KEY")
    if gemini_key:
        print(f"🔑 GEMINI_API_KEY가 설정되었습니다. (키 일부: {gemini_key[:10]}...)")
    else:
        print("⚠️  GEMINI_API_KEY 환경변수가 설정되지 않았습니다.")
        print("   더미 임베딩을 사용합니다. 실제 AI 응답을 받으려면 Gemini API 키를 설정하세요.")

    # Wait for database to be ready
    wait_for_db()

    # Setup pgvector and create table
    conn, embedding_dim = setup_pgvector()

    try:
        # Insert sample data
        print("\n📚 샘플 데이터 삽입 중...")
        insert_sample_data(conn, embedding_dim)

        # Start interactive chat
        interactive_chat(conn, embedding_dim)

    finally:
        conn.close()
        print("\n👋 데이터베이스 연결 종료")


if __name__ == "__main__":
    main()

