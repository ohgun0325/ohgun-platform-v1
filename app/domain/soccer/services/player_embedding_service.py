"""선수(player) 임베딩 서비스

jhgan/ko-sroberta-multitask 모델(768차원)을 사용하여
player 테이블의 선수 데이터를 임베딩하고 players_embeddings 테이블에 저장합니다.
"""

from __future__ import annotations

import logging
from typing import Any

from app.core.database import get_db_connection
from app.spokes.infrastructure.embedding_client import EmbeddingClient

logger = logging.getLogger(__name__)

# DB 벡터 차원 (jhgan/ko-sroberta-multitask 고정)
DB_EMBEDDING_DIM = 768


def index_player_embeddings(
    limit: int | None = None,
    add: bool = True,
) -> dict[str, Any]:
    """player 테이블의 선수 데이터를 임베딩하여 players_embeddings에 저장합니다.

    Args:
        limit: 처리할 최대 레코드 수 (None이면 전체)
        add: True(기본값)이면 기존 임베딩 유지·신규만 추가, False이면 기존 삭제 후 전체 재생성

    Returns:
        {
            "indexed": 새로 인덱싱된 레코드 수,
            "skipped": 건너뛴 레코드 수,
            "errors": 오류 목록,
            "message": 결과 메시지
        }

    Note:
        - EmbeddingClient를 사용하여 로컬 jhgan/ko-sroberta-multitask 모델(768차원)로 임베딩
        - add=True: players_embeddings에 없는 player_id만 임베딩
        - add=False: players_embeddings 테이블을 비우고 전체 재인덱싱
    """
    conn = get_db_connection()
    indexed = 0
    skipped = 0
    errors = []

    try:
        with conn.cursor() as cur:
            # 1) 기존 레코드 수 확인
            cur.execute("SELECT COUNT(*) FROM player")
            n_before = cur.fetchone()[0]

            if n_before == 0:
                return {
                    "indexed": 0,
                    "skipped": 0,
                    "errors": [],
                    "message": "player 테이블이 비어 있습니다.",
                }

            # 2) add=False이면 기존 임베딩 삭제
            if not add:
                cur.execute("DELETE FROM players_embeddings")
                conn.commit()
                logger.info(
                    f"[player 임베딩] 기존 players_embeddings 테이블 초기화 완료"
                )

            # 3) 임베딩 대상 선수 조회 (player 테이블 PK는 id, 등번호 컬럼은 back_no)
            if add:
                # add=True: players_embeddings에 없는 선수만
                query = """
                    SELECT p.id, p.player_name, p.team_id, p.position,
                           p.back_no, p.birth_date, p.height, p.weight
                    FROM player p
                    LEFT JOIN players_embeddings pe ON p.id = pe.player_id
                    WHERE pe.player_id IS NULL
                """
                if limit:
                    query += f" LIMIT {limit}"
            else:
                # add=False: 전체 선수
                query = """
                    SELECT id, player_name, team_id, position,
                           back_no, birth_date, height, weight
                    FROM player
                """
                if limit:
                    query += f" LIMIT {limit}"

            cur.execute(query)
            rows = cur.fetchall()

            if not rows:
                if add:
                    return {
                        "indexed": 0,
                        "skipped": n_before,
                        "errors": [],
                        "message": f"정상: player 테이블 선수 {n_before}명이 이미 players_embeddings에 모두 존재합니다. 추가할 대상이 없어 생략했습니다. (전체를 jhgan으로 다시 임베딩하려면 add=False로 전체 재인덱싱을 실행하세요.)",
                    }
                else:
                    return {
                        "indexed": 0,
                        "skipped": 0,
                        "errors": [],
                        "message": "player 테이블에 데이터가 없습니다.",
                    }

            # 4) 텍스트 생성 및 임베딩
            texts = []
            for row in rows:
                (
                    player_id,
                    player_name,
                    team_id,
                    position,
                    back_number,
                    birth_date,
                    height,
                    weight,
                ) = row
                text = (
                    f"선수명: {player_name or ''}, "
                    f"팀: {team_id or ''}, "
                    f"포지션: {position or ''}, "
                    f"등번호: {back_number or ''}, "
                    f"생년월일: {birth_date or ''}, "
                    f"키: {height or ''}cm, "
                    f"몸무게: {weight or ''}kg"
                )
                texts.append(text)

            # EmbeddingClient로 임베딩 생성 (jhgan/ko-sroberta-multitask, 768차원)
            client = EmbeddingClient()
            embeddings = client.embed_documents(texts)

            # 5) players_embeddings 테이블에 삽입
            insert_query = """
                INSERT INTO players_embeddings (player_id, content, embedding)
                VALUES (%s, %s, %s)
                ON CONFLICT (player_id) DO UPDATE SET
                    content = EXCLUDED.content,
                    embedding = EXCLUDED.embedding
            """

            for i, row in enumerate(rows):
                player_id = row[0]
                try:
                    cur.execute(
                        insert_query,
                        (player_id, texts[i], embeddings[i]),
                    )
                    indexed += 1
                except Exception as e:
                    errors.append({"player_id": player_id, "error": str(e)})
                    logger.error(
                        f"[player 임베딩] player_id={player_id} 임베딩 실패: {e}"
                    )

            conn.commit()

            # 6) 결과 메시지
            if add:
                msg = f"players_embeddings에 {indexed}건 추가 완료 (중복/오류 제외 {skipped}건)."
            else:
                msg = f"players_embeddings에 {indexed}건 인덱싱 완료."

            logger.info(f"[player 임베딩] {msg}")

            return {
                "indexed": indexed,
                "skipped": skipped,
                "errors": errors,
                "message": msg,
            }

    except Exception as e:
        logger.error(f"[player 임베딩] 오류 발생: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()
