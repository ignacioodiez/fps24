"""Destacadas de la semana (GET /destacadas): estrenos en España y sesiones especiales con buena nota."""
from collections import Counter, defaultdict
from datetime import date, datetime, time, timedelta

from sqlalchemy.orm import contains_eager, selectinload
from sqlmodel import Session, select

from app.database.models import Pase, Pelicula
from app.services.tiempo import ahora_madrid

MAX_ESTRENOS = 4
MAX_ESPECIALES = 7
VOTOS_MIN_ESTRENO = 50
VOTOS_MIN_ESPECIAL = 150


def semana(ahora: datetime) -> tuple:
    """(lunes, domingo) de la semana natural que contiene `ahora`."""
    lunes = ahora.date() - timedelta(days=ahora.weekday())
    return lunes, lunes + timedelta(days=6)


def leer_destacadas(session: Session, ahora: datetime = None) -> dict:
    """`ahora` en hora de Madrid sin tzinfo, como pase.fecha_hora: los límites son horas locales y el
    cambio de hora no los mueve (el domingo de 25 horas sigue acabando a las 24:00 locales)."""
    ahora = ahora or ahora_madrid()
    lunes, domingo = semana(ahora)
    pases = session.exec(
        select(Pase).join(Pelicula)
        .options(contains_eager(Pase.pelicula), selectinload(Pase.cine_rel))
        .where(Pase.activo, Pase.fecha_hora >= ahora,
               Pase.fecha_hora < datetime.combine(domingo + timedelta(days=1), time()),
               Pelicula.nota_tmdb.is_not(None), Pelicula.votos >= min(VOTOS_MIN_ESTRENO, VOTOS_MIN_ESPECIAL))
        .order_by(Pase.fecha_hora, Pase.id)
    ).all()

    pases_de = defaultdict(list)  # pelicula_id -> sus pases, por fecha
    for pase in pases:
        pases_de[pase.pelicula_id].append(pase)

    def por_nota(listas):
        return sorted(listas, key=lambda ps: (-ps[0].pelicula.nota_tmdb, -ps[0].pelicula.votos, ps[0].pelicula_id))

    estrenos = por_nota(ps for ps in pases_de.values()
                        if lunes <= (ps[0].pelicula.fecha_estreno or date.min) <= domingo
                        and ps[0].pelicula.votos >= VOTOS_MIN_ESTRENO)[:MAX_ESTRENOS]
    en_estrenos = {ps[0].pelicula_id for ps in estrenos}

    # Los eventos (ópera, ballet, directos) no tienen tmdb_id: el gestor no los busca en TMDB
    especiales_de = {id_: [p for p in ps if p.es_evento_especial] for id_, ps in pases_de.items()
                     if id_ not in en_estrenos and ps[0].pelicula.tmdb_id
                     and ps[0].pelicula.votos >= VOTOS_MIN_ESPECIAL}
    candidatas = por_nota(ps for ps in especiales_de.values() if ps)[:MAX_ESPECIALES]
    dias = Counter()
    especiales = []
    for ps in candidatas:  # por nota: la mejor elige día primero
        pase = min(ps, key=lambda p: (dias[p.fecha_hora.date()], p.fecha_hora, p.id))
        dias[pase.fecha_hora.date()] += 1
        especiales.append(dict(pelicula=pase.pelicula, pase=pase, nota=pase.pelicula.nota_tmdb))

    return dict(
        semana=dict(inicio=lunes, fin=domingo),
        estrenos=[dict(pelicula=ps[0].pelicula, fecha_estreno=ps[0].pelicula.fecha_estreno,
                       votos=ps[0].pelicula.votos, pases=len(ps), cines=len({p.cine_id for p in ps}),
                       primera_sesion=ps[0]) for ps in estrenos],
        especiales=especiales,
    )
