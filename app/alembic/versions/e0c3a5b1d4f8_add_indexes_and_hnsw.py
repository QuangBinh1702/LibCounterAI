"""Add indexes for events.timestamp, sessions.entry_at, and HNSW on embeddings

Revision ID: e0c3a5b1d4f8
Revises: 54e844cf69c2
Create Date: 2026-07-09 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import engine_from_config
from sqlalchemy.engine import reflection


revision: str = 'e0c3a5b1d4f8'
down_revision: Union[str, Sequence[str], None] = '54e844cf69c2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(op.f('ix_events_timestamp'), 'events', ['timestamp'], unique=False)
    op.create_index(op.f('ix_visit_sessions_entry_at'), 'visit_sessions', ['entry_at'], unique=False)

    bind = op.get_bind()
    if bind.engine.name == 'postgresql':
        op.execute(
            'CREATE INDEX IF NOT EXISTS ix_face_templates_embedding_hnsw '
            'ON face_templates USING hnsw (embedding_vector vector_cosine_ops) '
            'WITH (m = 16, ef_construction = 200);'
        )
        op.execute(
            'CREATE INDEX IF NOT EXISTS ix_unknown_identities_embedding_hnsw '
            'ON unknown_identities USING hnsw (embedding_vector vector_cosine_ops) '
            'WITH (m = 16, ef_construction = 200);'
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.engine.name == 'postgresql':
        op.execute('DROP INDEX IF EXISTS ix_unknown_identities_embedding_hnsw;')
        op.execute('DROP INDEX IF EXISTS ix_face_templates_embedding_hnsw;')

    op.drop_index(op.f('ix_visit_sessions_entry_at'), table_name='visit_sessions')
    op.drop_index(op.f('ix_events_timestamp'), table_name='events')
