"""Qué sale en la newsletter: la misma selección y orden por nota que /estrenos y /especiales
(services/destacadas.py), pero en su propia ventana (ventana()): el día de envío en Madrid y los 6 siguientes, no la
semana natural de destacadas.semana(). Las películas ocultas por el admin ya no llegan (_pases_por_pelicula las quita)."""
import re
from datetime import date, datetime, time, timedelta

from sqlmodel import Session

from app.services import destacadas as d
from app.services.tiempo import ahora_madrid

MAX_ESTRENOS = 6
MAX_ESPECIALES = 4
HORA_ENVIO = 16  # hora de Madrid a la que sale los lunes


def momento_envio(fecha: date) -> datetime:
    """Envío simulado (--fecha, ?fecha=): ese día a la hora del envío, en hora de Madrid sin tzinfo."""
    return datetime.combine(fecha, time(HORA_ENVIO))


def ventana(envio: datetime) -> tuple:
    """(primer día, último día) de la newsletter: el día del envío y los 6 siguientes. El lunes 26/10 a las 16:00,
    del 26/10 al 1/11; un envío en miércoles iría de miércoles a martes. Las sesiones cuentan desde `envio`."""
    return envio.date(), envio.date() + timedelta(days=6)


def poster_w342(url):
    """Los pósters se guardan en w500: en el correo, w342 (mitad de peso, de sobra para 252 px de ancho)."""
    return re.sub(r"/t/p/[^/]+/", "/t/p/w342/", url) if url else None


def mejor_sesion(elegida, pases):
    """La primera en VOSE entre `pases` (van por fecha); si no hay ninguna, la que eligió la selección."""
    return next((p for p in pases if p.idioma == "VOSE"), elegida)


def _fila(elegida, pases):
    peli, sesion = elegida.pelicula, mejor_sesion(elegida, pases)
    return dict(id=peli.id, titulo=peli.titulo, anio=peli.anio, poster=poster_w342(peli.poster_url),
                cines=len({p.cine_id for p in pases}), cine=sesion.cine, fecha_hora=sesion.fecha_hora,
                vose=sesion.idioma == "VOSE")


def datos_semana(session: Session, ahora: datetime = None) -> dict:
    """`ahora`: momento del envío en hora de Madrid sin tzinfo (por defecto, ahora mismo)."""
    ahora = ahora or ahora_madrid()
    desde, hasta = ventana(ahora)
    pases_de = d._pases_por_pelicula(session, ahora, desde, hasta)  # de `ahora` al final de `hasta`
    return dict(
        desde=desde, hasta=hasta,
        estrenos=[_fila(s, ps) for s, ps, _ in d.seleccionar_estrenos(pases_de, desde, hasta)[:MAX_ESTRENOS]],
        especiales=[_fila(s, ps) for s, ps, _ in d.seleccionar_especiales(pases_de, desde, hasta)[:MAX_ESPECIALES]],
    )
