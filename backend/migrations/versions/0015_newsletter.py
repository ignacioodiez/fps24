"""suscriptor y newsletter_envio: newsletter semanal con doble opt-in

Revision ID: 0015
Revises: 0014
Create Date: 2026-10-24 23:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '0015'
down_revision: Union[str, Sequence[str], None] = '0014'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Como 0014, más las secuencias de los id. Los roles solo existen en Supabase.
SQL_RLS = """
ALTER TABLE public.suscriptor ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.newsletter_envio ENABLE ROW LEVEL SECURITY;
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon')
       AND EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
        REVOKE ALL ON public.suscriptor, public.newsletter_envio FROM anon, authenticated;
        REVOKE ALL ON SEQUENCE public.suscriptor_id_seq, public.newsletter_envio_id_seq FROM anon, authenticated;
    END IF;
END
$$;
"""


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('suscriptor',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('email', sa.Text(), nullable=False),
    sa.Column('estado', sa.Text(), server_default='pendiente', nullable=False),
    sa.Column('token_confirmacion', sa.Text(), nullable=True),
    sa.Column('token_baja', sa.Text(), nullable=False),
    sa.Column('confirmaciones_enviadas', sa.SmallInteger(), server_default='0', nullable=False),
    sa.Column('confirmacion_enviada_en', sa.DateTime(timezone=True), nullable=True),
    sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
    sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.Column('confirmado_en', sa.DateTime(timezone=True), nullable=True),
    sa.Column('baja_en', sa.DateTime(timezone=True), nullable=True),
    sa.CheckConstraint("estado IN ('pendiente', 'activo', 'baja')", name='ck_suscriptor_estado'),
    sa.CheckConstraint('email = lower(email)', name='ck_suscriptor_email_minusculas'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('email', name='uq_suscriptor_email'),
    sa.UniqueConstraint('token_confirmacion', name='uq_suscriptor_token_confirmacion'),
    sa.UniqueConstraint('token_baja', name='uq_suscriptor_token_baja')
    )
    op.create_table('newsletter_envio',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('semana', sa.Text(), nullable=False),
    sa.Column('enviado_en', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.Column('destinatarios', sa.Integer(), server_default='0', nullable=False),
    sa.Column('ok', sa.Integer(), server_default='0', nullable=False),
    sa.Column('errores', sa.Integer(), server_default='0', nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('semana', name='uq_newsletter_envio_semana')
    )
    op.execute(SQL_RLS)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('newsletter_envio')
    op.drop_table('suscriptor')
