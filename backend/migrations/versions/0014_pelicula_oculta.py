"""pelicula_oculta: películas que el admin quita de /destacadas, /estrenos y /especiales

Revision ID: 0014
Revises: 0013
Create Date: 2026-10-24 22:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0014'
down_revision: Union[str, Sequence[str], None] = '0013'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Como 0013: sin FORCE ni políticas (el backend conecta como postgres). Los roles solo existen en Supabase.
# Sin secuencia que revocar: la clave es pelicula_id.
SQL_RLS = """
ALTER TABLE public.pelicula_oculta ENABLE ROW LEVEL SECURITY;
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon')
       AND EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
        REVOKE ALL ON public.pelicula_oculta FROM anon, authenticated;
    END IF;
END
$$;
"""


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('pelicula_oculta',
    sa.Column('pelicula_id', sa.Integer(), nullable=False),
    sa.Column('motivo', sa.Text(), nullable=True),
    sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.ForeignKeyConstraint(['pelicula_id'], ['pelicula.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('pelicula_id')
    )
    op.execute(SQL_RLS)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('pelicula_oculta')
