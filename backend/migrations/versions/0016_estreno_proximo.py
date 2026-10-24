"""estreno_proximo: próximos estrenos en España (TMDB) para /proximamente

Revision ID: 0016
Revises: 0015
Create Date: 2026-10-24 23:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0016'
down_revision: Union[str, Sequence[str], None] = '0015'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Como 0014: sin FORCE ni políticas, y sin secuencia (la clave es tmdb_id). Los roles solo existen en Supabase.
SQL_RLS = """
ALTER TABLE public.estreno_proximo ENABLE ROW LEVEL SECURITY;
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon')
       AND EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
        REVOKE ALL ON public.estreno_proximo FROM anon, authenticated;
    END IF;
END
$$;
"""


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('estreno_proximo',
    sa.Column('tmdb_id', sa.Integer(), autoincrement=False, nullable=False),
    sa.Column('titulo', sa.Text(), nullable=False),
    sa.Column('titulo_original', sa.Text(), nullable=True),
    sa.Column('fecha_es', sa.Date(), nullable=False),
    sa.Column('fecha_confirmada', sa.Boolean(), server_default=sa.false(), nullable=False),
    sa.Column('poster_path', sa.Text(), nullable=False),
    sa.Column('sinopsis', sa.Text(), nullable=True),
    sa.Column('popularidad', sa.Float(), nullable=True),
    sa.Column('votos', sa.Integer(), nullable=True),
    sa.Column('generos', sa.Text(), nullable=True),
    sa.Column('idioma_original', sa.Text(), nullable=True),
    sa.Column('actualizado_en', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.PrimaryKeyConstraint('tmdb_id')
    )
    op.create_index('ix_estreno_proximo_fecha_es', 'estreno_proximo', ['fecha_es'], unique=False)
    op.execute(SQL_RLS)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_estreno_proximo_fecha_es', table_name='estreno_proximo')
    op.drop_table('estreno_proximo')
