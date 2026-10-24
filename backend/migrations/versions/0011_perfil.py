"""perfil: nombre de usuario único y visibilidad (privado por defecto) de cada usuario de Supabase Auth

Revision ID: 0011
Revises: 0010
Create Date: 2026-10-24 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '0011'
down_revision: Union[str, Sequence[str], None] = '0010'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Como 0009 y 0010: sin FORCE ni políticas (el backend conecta como postgres). Los roles solo existen en Supabase.
# Sin secuencia que revocar: la clave es el user_id.
SQL_RLS = """
ALTER TABLE public.perfil ENABLE ROW LEVEL SECURITY;
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon')
       AND EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
        REVOKE ALL ON public.perfil FROM anon, authenticated;
    END IF;
END
$$;
"""


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('perfil',
    # sub del JWT de Supabase, como diario_entrada.user_id; sin FK a auth.users
    sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('usuario', sa.Text(), nullable=False),
    sa.Column('bio', sa.Text(), nullable=True),
    sa.Column('visibilidad', sa.Text(), server_default='privado', nullable=False),
    sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.Column('actualizado_en', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.CheckConstraint('char_length(bio) <= 160', name='ck_perfil_bio'),
    sa.CheckConstraint("visibilidad IN ('privado', 'publico')", name='ck_perfil_visibilidad'),
    sa.PrimaryKeyConstraint('user_id')
    )
    op.create_index('uq_perfil_usuario', 'perfil', [sa.text('lower(usuario)')], unique=True)
    op.execute(SQL_RLS)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('perfil')
