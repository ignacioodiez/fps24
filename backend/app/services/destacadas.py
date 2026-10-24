"""Destacadas de la semana (GET /destacadas): estrenos en España y sesiones especiales con buena nota.
También las páginas completas GET /estrenos y GET /especiales, por semanas."""
import re
from collections import Counter, defaultdict
from datetime import date, datetime, time, timedelta

from sqlalchemy import or_
from sqlalchemy.orm import contains_eager, selectinload
from sqlmodel import Session, select

from app.database.models import Pase, Pelicula, PeliculaOculta
from app.services.gestor_peliculas import analizar_titulo
from app.services.tiempo import ahora_madrid

MAX_ESTRENOS = 4
MAX_ESPECIALES = 7
VOTOS_MIN_ESTRENO = 10
VOTOS_MIN_ESPECIAL = 150
CINES_MIN_RELLENO = 2        # estrenos sin nota suficiente que rellenan hasta MAX_ESTRENOS
TIPO_CINE_ESPECIAL = "autor"  # especiales: solo pases de cines de este cine.tipo
SEMANAS_MAX = 3               # /especiales: de la semana actual (0) a la 3
SEMANAS_MAX_ESTRENOS = 8      # /estrenos: hasta la 8, con los próximos estrenos de TMDB (app/proximamente)
MAX_ESPECIALES_PAGINA = 30    # tope de seguridad de /especiales

# /especiales: solo cine. Los eventos sin tmdb_id ya no entran; esto quita los que sí están en TMDB
# (giras de conciertos, directos) y los que se colaran con un título de evento.
_NO_CINE = re.compile(r"EN DIRECTO|DIFERIDO|WORLD TOUR|LIVE VIEWING|NATIONAL THEATRE|NT LIVE", re.IGNORECASE)


def semana(ahora: datetime) -> tuple:
    """(lunes, domingo) de la semana natural que contiene `ahora`."""
    lunes = ahora.date() - timedelta(days=ahora.weekday())
    return lunes, lunes + timedelta(days=6)


def _con_nota(pelicula: Pelicula, votos_min: int) -> bool:
    return pelicula.nota_tmdb is not None and (pelicula.votos or 0) >= votos_min


def es_cine(pelicula: Pelicula) -> bool:
    """False si el título o los géneros delatan un evento (ópera, ballet, concierto, directo, teatro)."""
    generos = {g.strip() for g in (pelicula.generos or "").split(",")}
    return not (analizar_titulo(pelicula.titulo).evento or _NO_CINE.search(pelicula.titulo)
                or {"Documental", "Música"} <= generos)


def _pases_por_pelicula(session: Session, desde: datetime, lunes: date, domingo: date) -> dict:
    """pelicula_id -> sus pases activos de `desde` al final del domingo, por fecha: estrenos de la semana y especiales.
    Sin las películas ocultas por el admin (pelicula_oculta)."""
    pases = session.exec(
        select(Pase).join(Pelicula)
        .options(contains_eager(Pase.pelicula), selectinload(Pase.cine_rel))
        .where(Pase.activo, Pase.fecha_hora >= desde,
               Pase.fecha_hora < datetime.combine(domingo + timedelta(days=1), time()),
               or_(Pelicula.fecha_estreno.between(lunes, domingo), Pase.es_evento_especial),
               ~select(PeliculaOculta.pelicula_id).where(PeliculaOculta.pelicula_id == Pelicula.id).exists())
        .order_by(Pase.fecha_hora, Pase.id)
    ).all()
    pases_de = defaultdict(list)  # pelicula_id -> sus pases, por fecha
    for pase in pases:
        pases_de[pase.pelicula_id].append(pase)
    return pases_de


def _por_nota(listas):
    return sorted(listas, key=lambda ps: (-ps[0].pelicula.nota_tmdb, -ps[0].pelicula.votos, ps[0].pelicula_id))


def _cines(ps):
    return len({p.cine_id for p in ps})


def _alternativas(elegido: Pase, ps: list) -> list:
    """El mismo día que `elegido`, la primera sesión de cada uno de los otros cines entre `ps` (que va por fecha):
    la que se sugeriría si el usuario prefiere ese cine."""
    primeras = {}
    for p in ps:
        if p.fecha_hora.date() == elegido.fecha_hora.date() and p.cine_id != elegido.cine_id:
            primeras.setdefault(p.cine_id, p)
    return list(primeras.values())


def _de_la_semana(pases_de: dict, lunes: date, domingo: date) -> list:
    return [ps for ps in pases_de.values() if lunes <= (ps[0].pelicula.fecha_estreno or date.min) <= domingo]


def _elegir_especiales(pases_de: dict, vetadas: set, tope: int, filtro=lambda pelicula: True) -> list:
    """Por nota, una sesión por película: la mejor elige día primero y cada una coge el día menos repetido.
    -> [(pase elegido, pases especiales de la película)]"""
    # Los eventos (ópera, ballet, directos) no tienen tmdb_id: el gestor no los busca en TMDB
    especiales_de = {id_: [p for p in ps if p.es_evento_especial and p.cine_rel.tipo == TIPO_CINE_ESPECIAL]
                     for id_, ps in pases_de.items()
                     if id_ not in vetadas and ps[0].pelicula.tmdb_id and _con_nota(ps[0].pelicula, VOTOS_MIN_ESPECIAL)
                     and filtro(ps[0].pelicula)}
    candidatas = _por_nota(ps for ps in especiales_de.values() if ps)[:tope]
    dias = Counter()
    elegidas = []
    for ps in candidatas:
        pase = min(ps, key=lambda p: (dias[p.fecha_hora.date()], p.fecha_hora, p.id))
        dias[pase.fecha_hora.date()] += 1
        elegidas.append((pase, ps))
    return elegidas


def leer_destacadas(session: Session, ahora: datetime = None) -> dict:
    """`ahora` en hora de Madrid sin tzinfo, como pase.fecha_hora: los límites son horas locales y el
    cambio de hora no los mueve (el domingo de 25 horas sigue acabando a las 24:00 locales)."""
    ahora = ahora or ahora_madrid()
    lunes, domingo = semana(ahora)
    pases_de = _pases_por_pelicula(session, ahora, lunes, domingo)

    de_la_semana = _de_la_semana(pases_de, lunes, domingo)
    con_nota = _por_nota(ps for ps in de_la_semana if _con_nota(ps[0].pelicula, VOTOS_MIN_ESTRENO))[:MAX_ESTRENOS]
    ids_con_nota = {ps[0].pelicula_id for ps in con_nota}
    relleno = sorted((ps for ps in de_la_semana
                      if ps[0].pelicula_id not in ids_con_nota and _cines(ps) >= CINES_MIN_RELLENO),
                     key=lambda ps: (-_cines(ps), -len(ps), ps[0].pelicula_id))[:MAX_ESTRENOS - len(con_nota)]
    estrenos = [(ps, False) for ps in con_nota] + [(ps, True) for ps in relleno]
    vetadas = {ps[0].pelicula_id for ps, _ in estrenos}

    return dict(
        semana=dict(inicio=lunes, fin=domingo),
        estrenos=[dict(pelicula=ps[0].pelicula, fecha_estreno=ps[0].pelicula.fecha_estreno,
                       votos=ps[0].pelicula.votos, pases=len(ps), cines=_cines(ps), primera_sesion=ps[0],
                       alternativas=_alternativas(ps[0], ps), sin_nota=sin_nota) for ps, sin_nota in estrenos],
        especiales=[dict(pelicula=pase.pelicula, pase=pase, nota=pase.pelicula.nota_tmdb, alternativas=_alternativas(pase, ps))
                    for pase, ps in _elegir_especiales(pases_de, vetadas, MAX_ESPECIALES)],
    )


# --- Páginas /estrenos y /especiales. La consulta (_pases_por_pelicula) va separada de la selección
# (seleccionar_*). Las ocultas por el admin ya no llegan a la selección.

def _semana_n(n: int, ahora: datetime) -> tuple:
    """(lunes, domingo, desde) de la semana n (0 = la actual). En la actual solo cuenta lo que queda."""
    lunes = semana(ahora)[0] + timedelta(weeks=n)
    return lunes, lunes + timedelta(days=6), ahora if n == 0 else datetime.combine(lunes, time())


def seleccionar_estrenos(pases_de: dict, lunes: date, domingo: date) -> list:
    """Todos los estrenos de la semana con pases (solo cine: fuera giras de conciertos). Primero las de nota fiable,
    por nota; luego las sin nota o con pocos votos, por nº de cines y de sesiones (una nota de 6 votos no ordena);
    desempate por título. -> [(primera sesión, pases, sin_nota)]"""
    filas = [(ps, not _con_nota(ps[0].pelicula, VOTOS_MIN_ESTRENO))
             for ps in _de_la_semana(pases_de, lunes, domingo) if es_cine(ps[0].pelicula)]
    filas.sort(key=lambda f: (f[1], (-_cines(f[0]), -len(f[0])) if f[1] else (-f[0][0].pelicula.nota_tmdb,),
                              f[0][0].pelicula.titulo.casefold(), f[0][0].pelicula_id))
    return [(ps[0], ps, sin_nota) for ps, sin_nota in filas]


def seleccionar_especiales(pases_de: dict, lunes: date, domingo: date) -> list:
    """Como en destacadas, sin el tope de 7 y solo cine. Los estrenos de la semana van a /estrenos, no aquí.
    -> [(sesión elegida, pases especiales, False)]"""
    vetadas = {ps[0].pelicula_id for ps in _de_la_semana(pases_de, lunes, domingo)}
    return [(pase, ps, False) for pase, ps in _elegir_especiales(pases_de, vetadas, MAX_ESPECIALES_PAGINA, es_cine)]


def leer_pagina(session: Session, seleccionar, n: int = 0, ahora: datetime = None, maximo: int = SEMANAS_MAX) -> dict:
    """Semana n (0..maximo) de /estrenos o /especiales; `seleccionar`: seleccionar_estrenos o seleccionar_especiales."""
    lunes, domingo, desde = _semana_n(n, ahora or ahora_madrid())
    pases_de = _pases_por_pelicula(session, desde, lunes, domingo)
    return dict(
        semana=n, desde=lunes, hasta=domingo, hay_anterior=n > 0, hay_siguiente=n < maximo,
        peliculas=[dict(pelicula=sesion.pelicula, sin_nota=sin_nota, n_sesiones=len(ps), n_cines=_cines(ps),
                        sesion=sesion, alternativas=_alternativas(sesion, ps)) for sesion, ps, sin_nota in seleccionar(pases_de, lunes, domingo)],
    )
