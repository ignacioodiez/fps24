"""pelicula.tmdb_reintentar_en

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-22 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0005'
down_revision: Union[str, Sequence[str], None] = '0004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('pelicula', sa.Column('tmdb_reintentar_en', sa.DateTime(), nullable=True))
    # Las ya guardadas como "no encontradas" se reintentan en la siguiente ejecución
    op.execute("UPDATE pelicula SET tmdb_reintentar_en = now() AT TIME ZONE 'utc' "
               "WHERE tmdb_id IS NULL AND sinopsis = 'No encontrada en TMDB'")


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('pelicula', 'tmdb_reintentar_en')
