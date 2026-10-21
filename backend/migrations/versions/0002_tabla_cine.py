"""tabla cine

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-21 18:00:00.000000

"""
import logging
import re
import unicodedata
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = '0002'
down_revision: Union[str, Sequence[str], None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

logger = logging.getLogger("alembic.runtime.migration")

# Copia congelada de app/services/cines.py: no se importa nada de app/ para que
# esta migración dé siempre el mismo resultado aunque cambie el código.
CINES_CONOCIDOS = {
    "Cine MK2 Paz": "mk2-paz",
    "Cine Doré": "dore",
    "Cine Embajadores": "embajadores",
    "Cine Embajadores Río": "embajadores-rio",
    "Cine Estudio (CBA)": "cine-estudio",
    "Cines Verdi": "verdi",
    "Cinesa Proyecciones": "cinesa-proyecciones",
    "Cinesa Príncipe Pío": "cinesa-principe-pio",
    "Cineteca": "cineteca",
    "Golem Madrid": "golem",
    "Mk2 Palacio de Hielo": "mk2-palacio-hielo",
    "Renoir Plaza de España": "renoir-plaza-espana",
    "Renoir Princesa": "renoir-princesa",
    "Renoir Retiro": "renoir-retiro",
    "Sala Equis": "equis",
    "Yelmo Cines Ideal": "yelmo-ideal",
    "Palacio de la Prensa": "palacio-prensa",
}


def _normalizar(nombre: str) -> str:
    sin_tildes = unicodedata.normalize("NFKD", nombre).encode("ascii", "ignore").decode()
    return " ".join(sin_tildes.split()).lower()


def _slugify(nombre: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", _normalizar(nombre)).strip("-")


def upgrade() -> None:
    """Upgrade schema."""
    cine = op.create_table('cine',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('slug', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('nombre', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('ultima_ejecucion_ok', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_cine_slug'), 'cine', ['slug'], unique=True)

    # Rellenar con los cines que ya aparecen en pase.cine.
    por_nombre = {_normalizar(n): (n, s) for n, s in CINES_CONOCIDOS.items()}
    filas = {}
    for (nombre,) in op.get_bind().execute(sa.text("SELECT DISTINCT cine FROM pase")):
        conocido = por_nombre.get(_normalizar(nombre))
        if conocido:
            nombre_canonico, slug = conocido
        else:
            nombre_canonico, slug = " ".join(nombre.split()), _slugify(nombre)
            logger.warning("Cine desconocido %r: uso el slug %r", nombre, slug)
        filas.setdefault(slug, {"slug": slug, "nombre": nombre_canonico})
    if filas:
        op.bulk_insert(cine, sorted(filas.values(), key=lambda f: f["slug"]))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_cine_slug'), table_name='cine')
    op.drop_table('cine')
