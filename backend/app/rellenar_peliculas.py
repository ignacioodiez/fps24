"""Backfill de un solo uso (migración 0007): rellena votos, fecha_estreno, idioma_original, director e
imdb_id y refresca nota_tmdb de las películas con tmdb_id, con una petición a TMDB por película.
Idempotente: siempre sobrescribe esas columnas con lo que diga TMDB. Si TMDB falla, para (cortacircuito).
Uso: python -m app.rellenar_peliculas [--dry-run] [--limite N]"""
import argparse
import time

from sqlmodel import Session, select

from app.database.engine import engine
from app.database.models import Pelicula
from app.scrapers.comun import obtener_logger
from app.services import tmdb
from app.services.gestor_peliculas import _campos_tmdb

log = obtener_logger("app.scrapers.rellenar_peliculas")

CAMPOS = ("nota_tmdb", "votos", "fecha_estreno", "idioma_original", "director", "imdb_id")
PAUSA = 0.25  # segundos entre peticiones


def rellenar(session: Session, limite: int = None, dry_run: bool = False, pausa: float = PAUSA) -> dict:
    """Commit por película (salvo dry_run, que no escribe nada)."""
    tmdb.reiniciar_cortacircuito()
    consulta = select(Pelicula).where(Pelicula.tmdb_id.is_not(None)).order_by(Pelicula.id).limit(limite)
    resumen = dict(revisadas=0, cambiadas=0, con_estreno_es=0, sin_estreno_es=0, interrumpido=False)
    for i, pelicula in enumerate(session.exec(consulta).all()):
        if i and pausa:
            time.sleep(pausa)
        try:
            datos = tmdb.datos_por_id(pelicula.tmdb_id)
        except tmdb.TmdbNoDisponible as e:
            log.warning("TMDB no disponible, se para en la película %s: %s", pelicula.id, e)
            resumen["interrumpido"] = True
            break
        nuevos = {k: v for k, v in _campos_tmdb(datos, pelicula.titulo).items() if k in CAMPOS}
        cambios = {k: v for k, v in nuevos.items() if getattr(pelicula, k) != v}
        resumen["revisadas"] += 1
        resumen["con_estreno_es" if nuevos["fecha_estreno"] else "sin_estreno_es"] += 1
        if cambios:
            resumen["cambiadas"] += 1
            log.info("%s %r: %s", pelicula.id, pelicula.titulo, cambios)
        if cambios and not dry_run:
            for k, v in cambios.items():
                setattr(pelicula, k, v)
            session.add(pelicula)
            session.commit()
    if dry_run:
        session.rollback()
    return resumen


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dry-run", action="store_true", help="consulta TMDB pero no escribe")
    parser.add_argument("--limite", type=int, help="máximo de películas")
    args = parser.parse_args()
    with Session(engine) as session:
        log.info("Resumen: %s", rellenar(session, args.limite, args.dry_run))


if __name__ == "__main__":
    main()
