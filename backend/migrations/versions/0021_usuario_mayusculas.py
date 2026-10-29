"""usuario con mayúsculas: el nombre se guarda como lo escribe su dueño; único y buscado sin distinguir mayúsculas

Revision ID: 0021
Revises: 0020
Create Date: 2026-10-29 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0021'
down_revision: Union[str, Sequence[str], None] = '0020'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Desde 0011, uq_perfil_usuario ya es sobre lower(usuario) y la app guardaba todo en minúsculas. Lo que cambia es que
# ahora puede llegar "Nacho": se rehace el índice para que la BD quede así pase lo que pase (por si en alguna se creó
# a mano sobre la columna tal cual). Los datos no se tocan: los nombres que hay ya están en minúsculas y no chocan.


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("DROP INDEX IF EXISTS uq_perfil_usuario")
    op.create_index('uq_perfil_usuario', 'perfil', [sa.text('lower(usuario)')], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    # El código anterior da por hecho que el nombre está en minúsculas (compara la ruta en minúsculas con el nombre):
    # se pasan a minúsculas. No puede chocar: uq_perfil_usuario ya impedía dos nombres iguales salvo mayúsculas. El
    # índice se queda como estaba en 0011. Lo único que se pierde es la capitalización elegida.
    op.execute("UPDATE perfil SET usuario = lower(usuario) WHERE usuario <> lower(usuario)")
