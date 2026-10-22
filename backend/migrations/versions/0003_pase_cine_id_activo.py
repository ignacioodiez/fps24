"""pase: cine_id, activo, visto_ultima_vez

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-22 09:30:00.000000

"""
import logging
import re
import unicodedata
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0003'
down_revision: Union[str, Sequence[str], None] = '0002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

logger = logging.getLogger("alembic.runtime.migration")

# Copia congelada de la migración 0002 (mismo diccionario y normalización): no se
# importa nada de app/ ni de 0002 para que esta migración no cambie nunca.
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
    op.add_column('pase', sa.Column('cine_id', sa.Integer(), nullable=True))
    # server_default rellena las filas existentes con true.
    op.add_column('pase', sa.Column('activo', sa.Boolean(), server_default=sa.true(), nullable=False))
    # visto_ultima_vez se guarda en UTC (sin zona): el código que lo escriba debe usar UTC también.
    op.add_column('pase', sa.Column('visto_ultima_vez', sa.DateTime(), nullable=True))
    op.create_index(op.f('ix_pase_cine_id'), 'pase', ['cine_id'], unique=False)
    op.create_foreign_key('pase_cine_id_fkey', 'pase', 'cine', ['cine_id'], ['id'])

    conn = op.get_bind()
    conn.execute(sa.text("UPDATE pase SET visto_ultima_vez = now() AT TIME ZONE 'UTC'"))

    # Emparejar pase.cine -> cine.slug igual que la 0002 creó los cines.
    por_nombre = {_normalizar(n): s for n, s in CINES_CONOCIDOS.items()}
    ids = dict(conn.execute(sa.text("SELECT slug, id FROM cine")).all())
    for (nombre,) in conn.execute(sa.text("SELECT DISTINCT cine FROM pase")).all():
        cine_id = ids.get(por_nombre.get(_normalizar(nombre)) or _slugify(nombre))
        if cine_id is None:
            logger.warning("Cine sin emparejar %r: sus pases quedan con cine_id NULL", nombre)
            continue
        conn.execute(sa.text("UPDATE pase SET cine_id = :id WHERE cine = :nombre"),
                     {"id": cine_id, "nombre": nombre})


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('pase_cine_id_fkey', 'pase', type_='foreignkey')
    op.drop_index(op.f('ix_pase_cine_id'), table_name='pase')
    op.drop_column('pase', 'visto_ultima_vez')
    op.drop_column('pase', 'activo')
    op.drop_column('pase', 'cine_id')
