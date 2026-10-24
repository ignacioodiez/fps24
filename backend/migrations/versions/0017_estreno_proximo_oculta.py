"""estreno_proximo.oculta: el admin oculta de /estrenos un próximo estreno que aún no tiene ficha en pelicula

Revision ID: 0017
Revises: 0016
Create Date: 2026-10-25 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0017'
down_revision: Union[str, Sequence[str], None] = '0016'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Sin tabla nueva: la RLS y el REVOKE de 0016 ya cubren la columna
    op.add_column('estreno_proximo', sa.Column('oculta', sa.Boolean(), server_default=sa.false(), nullable=False))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('estreno_proximo', 'oculta')
