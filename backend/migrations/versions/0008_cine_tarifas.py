"""cine.tarifas (JSONB): precios de entrada, día del espectador y notas

Revision ID: 0008
Revises: 0007
Create Date: 2026-10-23 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '0008'
down_revision: Union[str, Sequence[str], None] = '0007'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema. Nullable y aditivo: los datos los rellena sincronizar_cines() (CINES_DATOS)."""
    op.add_column('cine', sa.Column('tarifas', postgresql.JSONB(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('cine', 'tarifas')
