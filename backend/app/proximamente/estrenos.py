"""GET /estrenos?semana=n (0..8): las películas con sesiones en nuestra BD, como siempre (destacadas.leer_pagina), y
detrás los próximos estrenos de esa semana de estreno_proximo sin sesiones (sin_sesiones: sin cines ni horarios)."""
from datetime import date, datetime

from sqlalchemy import nulls_last
from sqlmodel import Session, select

from app.database.models import EstrenoProximo, Pase, Pelicula, PeliculaOculta
from app.services.destacadas import SEMANAS_MAX_ESTRENOS, leer_pagina, seleccionar_estrenos
from app.services.tiempo import ahora_madrid

POSTER = "https://image.tmdb.org/t/p/w500"  # como pelicula.poster_url


def sin_sesiones(session: Session, desde: date, hasta: date, ahora: datetime) -> list:
    """Estrenos de estreno_proximo entre `desde` y `hasta` sin sesiones activas desde `ahora` (las que tienen ya
    salen en leer_pagina: se cruza por tmdb_id), sin las ocultas (oculta o, si ya tiene ficha, pelicula_oculta)."""
    misma = Pelicula.tmdb_id == EstrenoProximo.tmdb_id
    con_sesiones = select(Pase.id).join(Pelicula).where(misma, Pase.activo, Pase.fecha_hora >= ahora).exists()
    ficha_oculta = select(PeliculaOculta.pelicula_id).join(Pelicula).where(misma).exists()
    estrenos = session.exec(
        select(EstrenoProximo)
        .where(EstrenoProximo.fecha_es.between(desde, hasta), ~EstrenoProximo.oculta, ~con_sesiones, ~ficha_oculta)
        .order_by(EstrenoProximo.fecha_es, nulls_last(EstrenoProximo.popularidad.desc()), EstrenoProximo.tmdb_id)
    ).all()
    return [dict(pelicula=dict(id=None, tmdb_id=e.tmdb_id, titulo=e.titulo, poster_url=f"{POSTER}{e.poster_path}",
                               titulo_original=e.titulo_original if e.titulo_original != e.titulo else None,
                               sinopsis=e.sinopsis, generos=e.generos, fecha_estreno=e.fecha_es,
                               fecha_confirmada=e.fecha_confirmada),
                 sin_nota=True, n_sesiones=0, n_cines=0, sesion=None, alternativas=[], sin_sesiones=True)
            for e in estrenos]


def leer_estrenos(session: Session, n: int = 0, ahora: datetime = None) -> dict:
    ahora = ahora or ahora_madrid()
    pagina = leer_pagina(session, seleccionar_estrenos, n, ahora, maximo=SEMANAS_MAX_ESTRENOS)
    pagina["peliculas"] += sin_sesiones(session, pagina["desde"], pagina["hasta"], ahora)
    return pagina
