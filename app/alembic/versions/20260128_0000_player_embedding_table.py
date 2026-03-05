"""player_embedding table (RAG/semantic search)

Revision ID: player_emb_1536
Revises: 3fadf78a9843
Create Date: 2026-01-28

"""
from alembic import op

revision = "player_emb_1536"
down_revision = "3fadf78a9843"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute(
        """
        CREATE TABLE player_embedding (
            id BIGSERIAL PRIMARY KEY,
            player_id VARCHAR NOT NULL,
            embedding vector(1536) NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
            CONSTRAINT fk_player_embedding_player
                FOREIGN KEY (player_id) REFERENCES player(id) ON DELETE CASCADE
        )
        """
    )
    op.execute(
        "CREATE INDEX ix_player_embedding_player_id ON player_embedding (player_id)"
    )
    op.execute(
        """
        CREATE INDEX ix_player_embedding_embedding_ivfflat
        ON player_embedding
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100)
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_player_embedding_embedding_ivfflat")
    op.execute("DROP INDEX IF EXISTS ix_player_embedding_player_id")
    op.execute("DROP TABLE IF EXISTS player_embedding")
