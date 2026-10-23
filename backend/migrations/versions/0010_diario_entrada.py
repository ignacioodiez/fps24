"""diario_entrada: películas que cada usuario ha visto en sala (privado, por user_id de Supabase Auth)

Revision ID: 0010
Revises: 0009
Create Date: 2026-10-23 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '0010'
down_revision: Union[str, Sequence[str], None] = '0009'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Como 0009: sin FORCE ni políticas (el backend conecta como postgres). Los roles solo existen en Supabase.
SQL_RLS = """
ALTER TABLE public.diario_entrada ENABLE ROW LEVEL SECURITY;
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon')
       AND EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
        REVOKE ALL ON public.diario_entrada FROM anon, authenticated;
        REVOKE ALL ON SEQUENCE public.diario_entrada_id_seq FROM anon, authenticated;
    END IF;
END
$$;
"""


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('diario_entrada',
    sa.Column('id', sa.Integer(), nullable=False),
    # sub del JWT de Supabase; sin FK a auth.users (otro esquema, y no existe en el Postgres local)
    sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('pelicula_id', sa.Integer(), nullable=False),
    sa.Column('cine_id', sa.Integer(), nullable=True),
    sa.Column('pase_id', sa.Integer(), nullable=True),
    sa.Column('fecha_vista', sa.Date(), nullable=False),
    sa.Column('nota', sa.SmallInteger(), nullable=True),
    sa.Column('comentario', sa.Text(), nullable=True),
    sa.Column('repeticion', sa.Boolean(), server_default=sa.false(), nullable=False),
    sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.Column('actualizado_en', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.ForeignKeyConstraint(['pelicula_id'], ['pelicula.id']),
    sa.ForeignKeyConstraint(['cine_id'], ['cine.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['pase_id'], ['pase.id'], ondelete='SET NULL'),
    sa.CheckConstraint('nota BETWEEN 1 AND 10', name='ck_diario_entrada_nota'),
    sa.CheckConstraint('char_length(comentario) <= 2000', name='ck_diario_entrada_comentario'),
    sa.UniqueConstraint('user_id', 'pelicula_id', 'fecha_vista', name='uq_diario_entrada_usuario_pelicula_fecha'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_diario_entrada_usuario_fecha', 'diario_entrada', ['user_id', sa.text('fecha_vista DESC')])
    op.execute(SQL_RLS)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('diario_entrada')
