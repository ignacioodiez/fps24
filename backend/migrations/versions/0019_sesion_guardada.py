"""sesion_guardada: agenda privada de sesiones de cada usuario de Supabase Auth (copia de la sesión, tope en la app)

Revision ID: 0019
Revises: 0018
Create Date: 2026-10-27 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '0019'
down_revision: Union[str, Sequence[str], None] = '0018'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Como 0010: sin FORCE ni políticas (el backend conecta como postgres). Los roles solo existen en Supabase.
SQL_RLS = """
ALTER TABLE public.sesion_guardada ENABLE ROW LEVEL SECURITY;
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon')
       AND EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
        REVOKE ALL ON public.sesion_guardada FROM anon, authenticated;
        REVOKE ALL ON SEQUENCE public.sesion_guardada_id_seq FROM anon, authenticated;
    END IF;
END
$$;
"""


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('sesion_guardada',
    sa.Column('id', sa.Integer(), nullable=False),
    # sub del JWT de Supabase, como diario_entrada.user_id; sin FK a auth.users
    sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
    # Solo para casarla con la sesión viva (marca "Guardada" en la cartelera); el resto es copia
    sa.Column('pase_id', sa.Integer(), nullable=True),
    sa.Column('pelicula_id', sa.Integer(), nullable=True),
    sa.Column('titulo', sa.Text(), nullable=False),
    sa.Column('poster_url', sa.Text(), nullable=True),
    sa.Column('cine_id', sa.Integer(), nullable=True),
    sa.Column('cine_nombre', sa.Text(), nullable=False),
    sa.Column('cine_slug', sa.Text(), nullable=False),
    sa.Column('fecha', sa.Date(), nullable=False),
    sa.Column('hora', sa.Time(), nullable=False),
    sa.Column('idioma', sa.Text(), nullable=True),
    sa.Column('link_compra', sa.Text(), nullable=True),
    sa.Column('diario_entrada_id', sa.Integer(), nullable=True),
    sa.Column('creada_en', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.ForeignKeyConstraint(['pase_id'], ['pase.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['pelicula_id'], ['pelicula.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['cine_id'], ['cine.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['diario_entrada_id'], ['diario_entrada.id'], ondelete='SET NULL'),
    sa.UniqueConstraint('user_id', 'cine_nombre', 'fecha', 'hora', 'titulo', name='uq_sesion_guardada_usuario_sesion'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_sesion_guardada_usuario_fecha', 'sesion_guardada', ['user_id', 'fecha', 'hora'])
    # Para el SET NULL al borrar un pase (los scrapers y la fusión de películas borran pases)
    op.create_index('ix_sesion_guardada_pase_id', 'sesion_guardada', ['pase_id'])
    op.execute(SQL_RLS)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('sesion_guardada')
