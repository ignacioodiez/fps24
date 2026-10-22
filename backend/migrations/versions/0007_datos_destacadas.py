"""datos para destacadas: pelicula (votos, estreno ES, idioma, director, imdb, refresco TMDB), cine (ficha) y pase.creado_en

Revision ID: 0007
Revises: 0006
Create Date: 2026-10-22 22:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = '0007'
down_revision: Union[str, Sequence[str], None] = '0006'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TEXTO = sqlmodel.sql.sqltypes.AutoString

COLUMNAS = {
    'pelicula': [('votos', sa.Integer), ('fecha_estreno', sa.Date), ('idioma_original', TEXTO),
                 ('director', TEXTO), ('imdb_id', TEXTO), ('tmdb_actualizado_en', sa.DateTime)],
    'cine': [('direccion', TEXTO), ('web', TEXTO), ('zona', TEXTO), ('tipo', TEXTO), ('telefono', TEXTO),
             ('lat', sa.Float), ('lng', sa.Float)],
}


def upgrade() -> None:
    """Upgrade schema. Todo nullable y aditivo."""
    for tabla, columnas in COLUMNAS.items():
        for nombre, tipo in columnas:
            op.add_column(tabla, sa.Column(nombre, tipo(), nullable=True))
    # Sin default al añadirla, para que los pases existentes queden en NULL; luego el default para los nuevos
    op.add_column('pase', sa.Column('creado_en', sa.DateTime(), nullable=True))
    op.alter_column('pase', 'creado_en', server_default=sa.text("(now() AT TIME ZONE 'utc')"))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('pase', 'creado_en')
    for tabla, columnas in COLUMNAS.items():
        for nombre, _ in reversed(columnas):
            op.drop_column(tabla, nombre)
