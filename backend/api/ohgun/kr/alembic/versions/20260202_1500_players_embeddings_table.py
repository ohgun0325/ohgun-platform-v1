"""create players_embeddings table (NeonDB)

Revision ID: players_emb_768
Revises: c96d63c4c4aa
Create Date: 2026-02-02 15:00

"""
from alembic import op

revision = "players_emb_768"
down_revision = "c96d63c4c4aa"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("""
        CREATE TABLE players_embeddings (
            id BIGSERIAL PRIMARY KEY,
            player_id VARCHAR(20) NOT NULL REFERENCES player(id) ON DELETE CASCADE,
            content TEXT NOT NULL,
            embedding vector(768) NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX ix_players_embeddings_player_id ON players_embeddings (player_id)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_players_embeddings_player_id")
    op.execute("DROP TABLE IF EXISTS players_embeddings")
