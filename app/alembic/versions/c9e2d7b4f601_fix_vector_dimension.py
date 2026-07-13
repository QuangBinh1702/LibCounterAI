"""Fix embeddding_vector column to use explicit 128 dimensions

Revision ID: c9e2d7b4f601
Revises: dc4291a87bee
Create Date: 2026-07-13 16:50:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


revision: str = 'c9e2d7b4f601'
down_revision: Union[str, None] = 'dc4291a87bee'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index('idx_face_templates_embedding_hnsw', table_name='face_templates', if_exists=True)
    op.drop_index('idx_unknown_identities_embedding_hnsw', table_name='unknown_identities', if_exists=True)
    op.alter_column('face_templates', 'embedding_vector',
        type_=Vector(128),
        postgresql_using='embedding_vector::vector(128)')
    op.alter_column('unknown_identities', 'embedding_vector',
        type_=Vector(128),
        postgresql_using='embedding_vector::vector(128)')
    op.create_index('idx_face_templates_embedding_hnsw', 'face_templates',
        ['embedding_vector'], postgresql_using='hnsw',
        postgresql_ops={'embedding_vector': 'vector_cosine_ops'})
    op.create_index('idx_unknown_identities_embedding_hnsw', 'unknown_identities',
        ['embedding_vector'], postgresql_using='hnsw',
        postgresql_ops={'embedding_vector': 'vector_cosine_ops'})


def downgrade() -> None:
    op.drop_index('idx_face_templates_embedding_hnsw', table_name='face_templates', if_exists=True)
    op.drop_index('idx_unknown_identities_embedding_hnsw', table_name='unknown_identities', if_exists=True)
    op.alter_column('face_templates', 'embedding_vector',
        type_=Vector(),
        postgresql_using='embedding_vector::vector')
    op.alter_column('unknown_identities', 'embedding_vector',
        type_=Vector(),
        postgresql_using='embedding_vector::vector')
