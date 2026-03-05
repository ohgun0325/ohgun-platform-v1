"""players_embeddings UNIQUE(player_id) 추가 (NeonDB)

Append 시 ON CONFLICT (player_id) DO NOTHING 사용을 위해 필요.

Revision ID: players_emb_uq
Revises: players_emb_768
Create Date: 2026-02-03

"""
from alembic import op

revision = "players_emb_uq"
down_revision = "players_emb_768"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_players_embeddings_player_id",
        "players_embeddings",
        ["player_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_players_embeddings_player_id",
        "players_embeddings",
        type_="unique",
    )
