"""perfil.diario_publico: el usuario decide si su diario se ve en su perfil público (apagado por defecto)

Revision ID: 0012
Revises: 0011
Create Date: 2026-10-24 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0012'
down_revision: Union[str, Sequence[str], None] = '0011'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Solo una columna: la tabla ya tiene RLS (0011)
    op.add_column('perfil', sa.Column('diario_publico', sa.Boolean(), server_default=sa.false(), nullable=False))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('perfil', 'diario_publico')
