"""Cron diario de los próximos estrenos de /estrenos: python -m app.proximamente.actualizar

Pide a TMDB los estrenos en España de mañana a +8 semanas (servicio.candidatos), los guarda en estreno_proximo y borra:
- lo ya estrenado hace más de 7 días (mientras tanto sigue saliendo en la semana en curso);
- lo que aún no se ha estrenado y TMDB ya no devuelve (retrasado fuera de la ventana o bajo los umbrales), salvo lo
  oculto por el admin: si vuelve, sigue oculto.
El refresco nunca cambia `oculta`.
Si TMDB falla o no devuelve nada, sale con código 1 sin tocar la tabla (el cron de Render la marca como fallida).
Las ocultas (estreno_proximo.oculta o pelicula_oculta) se quitan al leer /estrenos: se nota sin esperar al cron.
Unas 100-110 peticiones a TMDB por ejecución, con servicio.PAUSA entre ellas."""
import sys
from datetime import date, timedelta

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert
from sqlmodel import Session, delete

from app.database.engine import engine
from app.database.models import EstrenoProximo
from app.proximamente import servicio
from app.services import tmdb
from app.services.tiempo import hoy_madrid

SEMANAS = 8
DIAS_TRAS_ESTRENO = 7


def ventana(hoy: date) -> tuple:
    return hoy + timedelta(days=1), hoy + timedelta(weeks=SEMANAS)


def refrescar(session: Session, filas: list, hoy: date) -> dict:
    """Upsert de `filas` (no vacía) y borrados. No hace commit."""
    desde, _ = ventana(hoy)
    stmt = insert(EstrenoProximo).values(filas)
    session.exec(stmt.on_conflict_do_update(
        index_elements=["tmdb_id"],
        set_={**{c: stmt.excluded[c] for c in filas[0] if c not in ("tmdb_id", "oculta")}, "actualizado_en": func.now()}))
    ids = [f["tmdb_id"] for f in filas]
    fuera = session.exec(delete(EstrenoProximo).where(EstrenoProximo.fecha_es >= desde, ~EstrenoProximo.oculta,
                                                      EstrenoProximo.tmdb_id.not_in(ids))).rowcount
    caducadas = session.exec(delete(EstrenoProximo).where(
        EstrenoProximo.fecha_es < hoy - timedelta(days=DIAS_TRAS_ESTRENO))).rowcount
    return dict(guardadas=len(filas), fuera=fuera, caducadas=caducadas)


def main(hoy: date = None) -> dict:
    hoy = hoy or hoy_madrid()
    desde, hasta = ventana(hoy)
    tmdb.reiniciar_cortacircuito()
    try:
        filas = servicio.candidatos(desde, hasta)
    except tmdb.TmdbNoDisponible as e:
        sys.exit(f"TMDB no disponible, no se toca estreno_proximo: {e}")
    if not filas:
        sys.exit("TMDB no ha devuelto ningún estreno: no se toca estreno_proximo")
    with Session(engine) as session:
        resumen = refrescar(session, filas, hoy)
        session.commit()
    print(f"{desde}..{hasta}: {resumen} ({tmdb.peticiones} peticiones a TMDB)")
    return resumen


if __name__ == "__main__":
    main()
