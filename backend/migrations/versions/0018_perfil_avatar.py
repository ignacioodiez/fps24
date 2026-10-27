"""perfil: avatar (iniciales con color de la paleta o póster de una película), usuario de Letterboxd y cines_publicos

Revision ID: 0018
Revises: 0017
Create Date: 2026-10-27 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0018'
down_revision: Union[str, Sequence[str], None] = '0017'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Solo columnas: la tabla ya tiene RLS (0011). Los colores válidos los decide app/perfil.py (PALETA_AVATAR).
    op.add_column('perfil', sa.Column('avatar_tipo', sa.Text(), server_default='iniciales', nullable=False))
    op.add_column('perfil', sa.Column('avatar_color', sa.Text(), nullable=True))
    op.add_column('perfil', sa.Column('avatar_pelicula_id', sa.Integer(), nullable=True))
    op.add_column('perfil', sa.Column('letterboxd_usuario', sa.Text(), nullable=True))
    op.add_column('perfil', sa.Column('cines_publicos', sa.Boolean(), server_default=sa.false(), nullable=False))
    op.create_foreign_key('fk_perfil_avatar_pelicula', 'perfil', 'pelicula', ['avatar_pelicula_id'], ['id'],
                          ondelete='SET NULL')
    op.create_check_constraint('ck_perfil_avatar_tipo', 'perfil', "avatar_tipo IN ('iniciales', 'pelicula')")
    op.create_check_constraint('ck_perfil_letterboxd', 'perfil', "letterboxd_usuario ~ '^[A-Za-z0-9_]{2,20}$'")


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('ck_perfil_letterboxd', 'perfil', type_='check')
    op.drop_constraint('ck_perfil_avatar_tipo', 'perfil', type_='check')
    op.drop_constraint('fk_perfil_avatar_pelicula', 'perfil', type_='foreignkey')
    for columna in ('cines_publicos', 'letterboxd_usuario', 'avatar_pelicula_id', 'avatar_color', 'avatar_tipo'):
        op.drop_column('perfil', columna)
