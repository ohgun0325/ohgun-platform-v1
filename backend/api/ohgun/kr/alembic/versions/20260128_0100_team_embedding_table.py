"""team_embedding table (RAG/semantic search)

Revision ID: team_emb_1536
Revises: player_emb_1536
Create Date: 2026-01-28

"""
from alembic import op

revision = "team_emb_1536"
down_revision = "player_emb_1536"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute(
        """
        CREATE TABLE team_embedding (
            id BIGSERIAL PRIMARY KEY,
            team_id VARCHAR NOT NULL,
            embedding vector(1536) NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
            CONSTRAINT fk_team_embedding_team
                FOREIGN KEY (team_id) REFERENCES team(id) ON DELETE CASCADE
        )
        """
    )
    op.execute(
        "CREATE INDEX ix_team_embedding_team_id ON team_embedding (team_id)"
    )
    op.execute(
        """
        CREATE INDEX ix_team_embedding_embedding_ivfflat
        ON team_embedding
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100)
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_team_embedding_embedding_ivfflat")
    op.execute("DROP INDEX IF EXISTS ix_team_embedding_team_id")
    op.execute("DROP TABLE IF EXISTS team_embedding")
