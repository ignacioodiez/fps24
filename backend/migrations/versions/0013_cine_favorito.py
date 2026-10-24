"""cine_favorito: cines favoritos de cada usuario de Supabase Auth (privado, sin límite)

Revision ID: 0013
Revises: 0012
Create Date: 2026-10-24 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '0013'
down_revision: Union[str, Sequence[str], None] = '0012'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Como 0010 y 0011: sin FORCE ni políticas (el backend conecta como postgres). Los roles solo existen en Supabase.
# Sin secuencia que revocar: la clave es (user_id, cine_id).
SQL_RLS = """
ALTER TABLE public.cine_favorito ENABLE ROW LEVEL SECURITY;
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon')
       AND EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
        REVOKE ALL ON public.cine_favorito FROM anon, authenticated;
    END IF;
END
$$;
"""


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('cine_favorito',
    # sub del JWT de Supabase, como diario_entrada.user_id; sin FK a auth.users
    sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('cine_id', sa.Integer(), nullable=False),
    sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.ForeignKeyConstraint(['cine_id'], ['cine.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('user_id', 'cine_id')
    )
    # La PK ya sirve para "mis favoritos" (empieza por user_id); este, para el CASCADE al borrar un cine
    op.create_index('ix_cine_favorito_cine_id', 'cine_favorito', ['cine_id'])
    op.execute(SQL_RLS)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('cine_favorito')
