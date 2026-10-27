"""amigos: amistad (solicitud + aceptación) y bloqueo; visibilidad de tres niveles (privado/amigos/publico) en el
perfil, el diario y los cines

Revision ID: 0020
Revises: 0019
Create Date: 2026-10-27 22:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '0020'
down_revision: Union[str, Sequence[str], None] = '0019'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Como 0011: sin FORCE ni políticas (el backend conecta como postgres). Los roles solo existen en Supabase.
# Sin secuencias que revocar: amistad.id es un UUID y bloqueo tiene clave compuesta.
SQL_RLS = """
ALTER TABLE public.amistad ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.bloqueo ENABLE ROW LEVEL SECURITY;
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon')
       AND EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
        REVOKE ALL ON public.amistad, public.bloqueo FROM anon, authenticated;
    END IF;
END
$$;
"""

# Una sección nunca más abierta que el perfil
def _ck_seccion(columna):
    return f"{columna} = 'privado' OR {columna} = visibilidad OR visibilidad = 'publico'"


def upgrade() -> None:
    """Upgrade schema."""
    # Perfil: 'amigos' entra como nivel; los booleanos pasan a texto con el mismo efecto que tenían: una sección se veía
    # solo con el perfil público Y su booleano, así que eso (y solo eso) pasa a 'publico'; lo demás, 'privado'.
    op.drop_constraint('ck_perfil_visibilidad', 'perfil', type_='check')
    op.create_check_constraint('ck_perfil_visibilidad', 'perfil', "visibilidad IN ('privado', 'amigos', 'publico')")
    for nueva, vieja in (('diario_visibilidad', 'diario_publico'), ('cines_visibilidad', 'cines_publicos')):
        op.add_column('perfil', sa.Column(nueva, sa.Text(), server_default='privado', nullable=False))
        op.execute(f"UPDATE perfil SET {nueva} = CASE WHEN visibilidad = 'publico' AND {vieja} THEN 'publico' ELSE 'privado' END")
        op.drop_column('perfil', vieja)
        op.create_check_constraint(f'ck_perfil_{nueva}', 'perfil', f"{nueva} IN ('privado', 'amigos', 'publico')")
        op.create_check_constraint(f'ck_perfil_{nueva}_perfil', 'perfil', _ck_seccion(nueva))
    # Tope diario de solicitudes nuevas (día de Madrid): cancelar y reenviar también cuenta
    op.add_column('perfil', sa.Column('solicitudes_dia', sa.Date(), nullable=True))
    op.add_column('perfil', sa.Column('solicitudes_hoy', sa.SmallInteger(), server_default='0', nullable=False))

    # Sin FK a auth.users (otro esquema, no existe en local): a perfil, que es lo que hace falta para tener amigos.
    # Borrar el perfil (la cuenta) borra sus amistades, solicitudes y bloqueos.
    op.create_table('amistad',
    sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('solicitante_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('destinatario_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('estado', sa.Text(), server_default='pendiente', nullable=False),
    sa.Column('creada_en', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.Column('respondida_en', sa.DateTime(timezone=True), nullable=True),
    sa.CheckConstraint("estado IN ('pendiente', 'aceptada')", name='ck_amistad_estado'),
    sa.CheckConstraint('solicitante_id <> destinatario_id', name='ck_amistad_distintos'),
    sa.ForeignKeyConstraint(['solicitante_id'], ['perfil.user_id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['destinatario_id'], ['perfil.user_id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    # Un único par sin importar quién la pidió
    op.create_index('uq_amistad_par', 'amistad', [sa.text('least(solicitante_id, destinatario_id)'),
                                                  sa.text('greatest(solicitante_id, destinatario_id)')], unique=True)
    op.create_index('ix_amistad_destinatario', 'amistad', ['destinatario_id'])
    op.create_table('bloqueo',
    sa.Column('bloqueador_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('bloqueado_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('creada_en', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.CheckConstraint('bloqueador_id <> bloqueado_id', name='ck_bloqueo_distintos'),
    sa.ForeignKeyConstraint(['bloqueador_id'], ['perfil.user_id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['bloqueado_id'], ['perfil.user_id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('bloqueador_id', 'bloqueado_id')
    )
    op.create_index('ix_bloqueo_bloqueado', 'bloqueo', ['bloqueado_id'])
    op.execute(SQL_RLS)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('bloqueo')
    op.drop_table('amistad')
    op.drop_column('perfil', 'solicitudes_hoy')
    op.drop_column('perfil', 'solicitudes_dia')
    # Hacia atrás, "amigos" se cierra a privado (nunca se abre de más)
    for nueva, vieja in (('diario_visibilidad', 'diario_publico'), ('cines_visibilidad', 'cines_publicos')):
        op.add_column('perfil', sa.Column(vieja, sa.Boolean(), server_default=sa.false(), nullable=False))
        op.execute(f"UPDATE perfil SET {vieja} = ({nueva} = 'publico')")
        op.drop_column('perfil', nueva)  # se lleva sus CHECK
    op.drop_constraint('ck_perfil_visibilidad', 'perfil', type_='check')
    op.execute("UPDATE perfil SET visibilidad = 'privado' WHERE visibilidad = 'amigos'")
    op.create_check_constraint('ck_perfil_visibilidad', 'perfil', "visibilidad IN ('privado', 'publico')")
