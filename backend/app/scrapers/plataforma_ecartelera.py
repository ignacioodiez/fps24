"""Cartelera de un cine en eCartelera por su id de ficha: una página por día en /cines/<id>,N,1.html (N = días desde
hoy, ~10 días que enlaza ul.days), con user agent propio y PAUSA entre páginas. Por div.titem, el título de p.tit, el
país de p.data y las horas de data-session-time. No da versión ni sala (data-session-format viene vacío).
Se rompe si: cambian las clases (days, titem, tit, data) o las URLs de día. Los enlaces de compra (/cines/comprar/,
de afiliado) no se siguen ni se guardan."""
import html
import re
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from sqlmodel import Session

from app.database.engine import engine
from app.scrapers.comun import FuenteNoDisponible, hoy_madrid, obtener_html, obtener_logger
from app.services.gestor_peliculas import resolver_pelicula
from app.services.pases import registrar_pase

URL_DIA = "https://www.ecartelera.com/cines/{id},{n},1.html"
USER_AGENT = "fps24-bot (+https://fps24.es)"
PRECIO = "Consultar"
PAUSA = 2.0
MAX_PETICIONES = 10
# shortcut: la versión sale del país (eCartelera no la da); si un día rellena data-session-format, usarlo
PAISES_EN_ESPANOL = {"España", "México", "Argentina", "Colombia", "Chile", "Perú", "Uruguay", "Venezuela", "Cuba"}

log = obtener_logger(__name__)


@dataclass(frozen=True)
class Sesion:
    titulo: str
    fecha_hora: datetime
    idioma: str


def leer_dias(pagina, id_cine):
    """HTML -> [N] de los días que enlaza ul.days (<id>,N,1.html), en orden."""
    dias = re.search(r'(?s)<ul class="days">(.*?)</ul>', pagina)
    if not dias:
        raise FuenteNoDisponible(f"{URL_DIA.format(id=id_cine, n=0)}: no hay lista de días")
    return [int(n) for n in re.findall(rf'href="https://www\.ecartelera\.com/cines/{id_cine},(\d+),1\.html"', dias.group(1))]


def leer_dia(pagina, fecha: date, contadores, cine, idioma_fijo=None):
    """HTML de un día -> [Sesion]. FuenteNoDisponible si la página no es de `fecha`.
    idioma_fijo: la versión de todos los pases si el cine la tiene decidida; si es None, sale del país."""
    marcado = re.search(r'<li class="on"><a [^>]*>[^<]*?(\d{1,2})</a>', pagina)
    if not marcado or int(marcado.group(1)) != fecha.day:
        raise FuenteNoDisponible(f"eCartelera: la página no es del día {fecha} ({marcado and marcado.group(0)!r})")
    sesiones = []
    for bloque in pagina.split('<div class="titem"')[1:]:
        titulo = re.search(r'<p class="tit"><a [^>]*>(.*?)</a>', bloque)
        if not titulo:
            log.warning("%s: película sin título el %s", cine, fecha)
            contadores["descartado"] += 1
            continue
        titulo = html.unescape(titulo.group(1)).strip()
        datos = re.search(r'<p class="data">(.*?)</p>', bloque)
        paises = {html.unescape(p).strip() for p in re.findall(r"<span>(.*?)</span>", datos.group(1) if datos else "")}
        idioma = idioma_fijo or ("Español" if paises & PAISES_EN_ESPANOL else "VOSE")
        for hora in re.findall(r'data-session-time="([^"]*)"', bloque):
            try:
                h, m = map(int, hora.split(":"))
                sesiones.append(Sesion(titulo, datetime(fecha.year, fecha.month, fecha.day, h, m), idioma))
            except ValueError:
                log.warning("Pase descartado de %r: %s %r", titulo, fecha, hora)
                contadores["descartado"] += 1
    return sesiones


def leer_cine(id_cine, cine, contadores, idioma_fijo=None, obtener=lambda url: obtener_html(url, USER_AGENT),
              dormir=time.sleep, hoy: date = None):
    """Sesiones de todos los días que enlaza la página de hoy, una petición por día con PAUSA entre ellas."""
    hoy = hoy or hoy_madrid()
    pagina = obtener(URL_DIA.format(id=id_cine, n=0))
    contadores["peticiones"] = 1
    sesiones = leer_dia(pagina, hoy, contadores, cine, idioma_fijo)
    for n in leer_dias(pagina, id_cine):
        if n == 0:
            continue
        if contadores["peticiones"] >= MAX_PETICIONES:
            log.info("%s: tope de %d peticiones, no se leen más días", cine, MAX_PETICIONES)
            break
        dormir(PAUSA)
        pagina = obtener(URL_DIA.format(id=id_cine, n=n))
        contadores["peticiones"] += 1
        sesiones += leer_dia(pagina, hoy + timedelta(days=n), contadores, cine, idioma_fijo)
    return sesiones


def scrapear(id_cine, cine, sala, link_compra, idioma_fijo=None):
    """Lee el cine y registra sus pases. sala forma parte de la identidad del pase: no cambiarla una vez en uso."""
    contadores = {"creado": 0, "actualizado": 0, "descartado": 0, "peticiones": 0}
    peliculas = {}  # título de la web -> (pelicula_id, es_especial)

    with Session(engine) as session:
        sesiones = leer_cine(id_cine, cine, contadores, idioma_fijo)
        if not sesiones:
            raise FuenteNoDisponible(f"{URL_DIA.format(id=id_cine, n=0)}: no hay sesiones de {cine}")
        for s in sesiones:
            if s.titulo not in peliculas:
                peliculas[s.titulo] = resolver_pelicula(session, s.titulo, cine)
            pelicula_id, es_especial = peliculas[s.titulo]
            if pelicula_id is None:
                contadores["descartado"] += 1
                continue
            resultado = registrar_pase(
                session,
                cine=cine,
                pelicula_id=pelicula_id,
                fecha_hora=s.fecha_hora,
                sala=sala,
                idioma=s.idioma,
                precio=PRECIO,
                link_compra=link_compra,
                es_evento_especial=es_especial,
            )
            contadores[resultado] += 1
        session.commit()
    log.info("%s: %s", cine, contadores)
