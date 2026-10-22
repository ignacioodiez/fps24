"""pelicula_alias e índice único parcial de pelicula.tmdb_id

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-22 12:00:00.000000

"""
import logging
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = '0004'
down_revision: Union[str, Sequence[str], None] = '0003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

logger = logging.getLogger("alembic.runtime.migration")


def _fusionar_tmdb_duplicados(conn) -> None:
    """Deja una película por tmdb_id (la de id menor) y le pasa los pases de las demás.
    Los pases que ya existen en la que se queda (mismo cine, fecha, idioma y sala) se borran."""
    duplicados = conn.execute(sa.text(
        "SELECT tmdb_id, array_agg(id ORDER BY id) FROM pelicula "
        "WHERE tmdb_id IS NOT NULL GROUP BY tmdb_id HAVING count(*) > 1")).all()
    for tmdb_id, ids in duplicados:
        queda, sobran = ids[0], ids[1:]
        logger.warning("tmdb_id %s duplicado en las películas %s: se queda la %s", tmdb_id, ids, queda)
        params = {"queda": queda, "sobran": sobran}
        conn.execute(sa.text(
            "DELETE FROM pase p USING pase k "
            "WHERE p.pelicula_id = ANY(:sobran) AND k.pelicula_id = :queda "
            "AND p.cine = k.cine AND p.fecha_hora = k.fecha_hora "
            "AND p.idioma IS NOT DISTINCT FROM k.idioma AND coalesce(p.sala, '') = coalesce(k.sala, '')"), params)
        conn.execute(sa.text("UPDATE pase SET pelicula_id = :queda WHERE pelicula_id = ANY(:sobran)"), params)
        conn.execute(sa.text("DELETE FROM pelicula WHERE id = ANY(:sobran)"), params)


def upgrade() -> None:
    """Upgrade schema."""
    _fusionar_tmdb_duplicados(op.get_bind())
    op.create_index('ix_pelicula_tmdb_id_unico', 'pelicula', ['tmdb_id'], unique=True,
                    postgresql_where=sa.text('tmdb_id IS NOT NULL'))

    op.create_table('pelicula_alias',
    sa.Column('titulo_norm', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('pelicula_id', sa.Integer(), nullable=False),
    sa.Column('creado_en', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['pelicula_id'], ['pelicula.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('titulo_norm')
    )
    op.create_index(op.f('ix_pelicula_alias_pelicula_id'), 'pelicula_alias', ['pelicula_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema. La fusión de duplicados no se deshace."""
    op.drop_index(op.f('ix_pelicula_alias_pelicula_id'), table_name='pelicula_alias')
    op.drop_table('pelicula_alias')
    op.drop_index('ix_pelicula_tmdb_id_unico', table_name='pelicula')
