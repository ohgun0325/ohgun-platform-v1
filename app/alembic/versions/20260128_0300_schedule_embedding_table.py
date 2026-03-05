"""schedule_embedding table (RAG/semantic search)

Revision ID: schedule_emb_1536
Revises: stadium_emb_1536
Create Date: 2026-01-28

"""
from alembic import op

revision = "schedule_emb_1536"
down_revision = "stadium_emb_1536"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute(
        """
        CREATE TABLE schedule_embedding (
            id BIGSERIAL PRIMARY KEY,
            schedule_id VARCHAR NOT NULL,
            embedding vector(1536) NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
            CONSTRAINT fk_schedule_embedding_schedule
                FOREIGN KEY (schedule_id) REFERENCES schedule(id) ON DELETE CASCADE
        )
        """
    )
    op.execute(
        "CREATE INDEX ix_schedule_embedding_schedule_id ON schedule_embedding (schedule_id)"
    )
    op.execute(
        """
        CREATE INDEX ix_schedule_embedding_embedding_ivfflat
        ON schedule_embedding
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100)
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_schedule_embedding_embedding_ivfflat")
    op.execute("DROP INDEX IF EXISTS ix_schedule_embedding_schedule_id")
    op.execute("DROP TABLE IF EXISTS schedule_embedding")
