"""pase: identidad única, cine_id NOT NULL y sin la columna de texto cine

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-22 20:00:00.000000

"""
import logging
import re
import unicodedata
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = '0006'
down_revision: Union[str, Sequence[str], None] = '0005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

logger = logging.getLogger("alembic.runtime.migration")

# Copia congelada de la migración 0003 (mismo diccionario y normalización): no se
# importa nada de app/ ni de otras migraciones para que esta no cambie nunca.
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

# Identidad de un pase. NULL en idioma o sala cuenta como '' (registrar_pase hace lo mismo con sala).
IDENTIDAD = "cine_id, pelicula_id, fecha_hora, coalesce(idioma, ''), coalesce(sala, '')"


def _normalizar(nombre: str) -> str:
    sin_tildes = unicodedata.normalize("NFKD", nombre).encode("ascii", "ignore").decode()
    return " ".join(sin_tildes.split()).lower()


def _slugify(nombre: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", _normalizar(nombre)).strip("-")


def _rellenar_cine_id(conn) -> None:
    por_nombre = {_normalizar(n): s for n, s in CINES_CONOCIDOS.items()}
    ids = dict(conn.execute(sa.text("SELECT slug, id FROM cine")).all())
    sin_resolver = []
    for (nombre,) in conn.execute(sa.text("SELECT DISTINCT cine FROM pase WHERE cine_id IS NULL")).all():
        cine_id = ids.get(por_nombre.get(_normalizar(nombre)) or _slugify(nombre))
        if cine_id is None:
            sin_resolver.append(nombre)
            continue
        conn.execute(sa.text("UPDATE pase SET cine_id = :id WHERE cine = :nombre AND cine_id IS NULL"),
                     {"id": cine_id, "nombre": nombre})
    if sin_resolver:
        raise RuntimeError(f"Pases con cine_id NULL cuyo cine no está en la tabla cine: {sin_resolver}. "
                           "Crea esos cines (o corrige pase.cine) y vuelve a lanzar la migración.")


def _deduplicar(conn) -> None:
    """Deja un pase por identidad: el activo y, dentro de eso, el visto más recientemente."""
    borrados = conn.execute(sa.text(
        "DELETE FROM pase WHERE id IN (SELECT id FROM ("
        f"  SELECT id, row_number() OVER (PARTITION BY {IDENTIDAD} "
        "     ORDER BY activo DESC, visto_ultima_vez DESC NULLS LAST, id DESC) AS n FROM pase) x "
        "WHERE n > 1)")).rowcount
    if borrados:
        logger.warning("Borrados %d pases duplicados", borrados)


def upgrade() -> None:
    """Upgrade schema. Ninguna tabla tiene FK a pase.id: borrar duplicados no deja nada colgando."""
    conn = op.get_bind()
    _rellenar_cine_id(conn)
    _deduplicar(conn)
    op.alter_column('pase', 'cine_id', existing_type=sa.Integer(), nullable=False)
    op.create_index('ux_pase_identidad', 'pase',
                    ['cine_id', 'pelicula_id', 'fecha_hora',
                     sa.text("coalesce(idioma, '')"), sa.text("coalesce(sala, '')")], unique=True)
    op.drop_column('pase', 'cine')


def downgrade() -> None:
    """Downgrade schema. Los duplicados borrados no vuelven."""
    op.add_column('pase', sa.Column('cine', sqlmodel.sql.sqltypes.AutoString(), nullable=True))
    op.execute("UPDATE pase SET cine = c.nombre FROM cine c WHERE c.id = pase.cine_id")
    op.alter_column('pase', 'cine', existing_type=sqlmodel.sql.sqltypes.AutoString(), nullable=False)
    op.drop_index('ux_pase_identidad', table_name='pase')
    op.alter_column('pase', 'cine_id', existing_type=sa.Integer(), nullable=True)
