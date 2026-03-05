"""stadium_embedding table (RAG/semantic search)

Revision ID: stadium_emb_1536
Revises: team_emb_1536
Create Date: 2026-01-28

"""
from alembic import op

revision = "stadium_emb_1536"
down_revision = "team_emb_1536"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute(
        """
        CREATE TABLE stadium_embedding (
            id BIGSERIAL PRIMARY KEY,
            stadium_id VARCHAR NOT NULL,
            embedding vector(1536) NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
            CONSTRAINT fk_stadium_embedding_stadium
                FOREIGN KEY (stadium_id) REFERENCES stadium(id) ON DELETE CASCADE
        )
        """
    )
    op.execute(
        "CREATE INDEX ix_stadium_embedding_stadium_id ON stadium_embedding (stadium_id)"
    )
    op.execute(
        """
        CREATE INDEX ix_stadium_embedding_embedding_ivfflat
        ON stadium_embedding
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100)
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_stadium_embedding_embedding_ivfflat")
    op.execute("DROP INDEX IF EXISTS ix_stadium_embedding_stadium_id")
    op.execute("DROP TABLE IF EXISTS stadium_embedding")
