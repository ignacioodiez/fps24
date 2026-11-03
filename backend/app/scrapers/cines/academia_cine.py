"""Lee: https://www.academiadecine.com/actividades/ (HTML de servidor) -> la ficha de cada actividad.
Extrae: del listado, fecha y hora ("04/Nov · 19:00") y título; de la ficha, si es una película en la sala de Madrid abierta
al público (sede "Sala de proyecciones", campo Formato y sin "exclusivo para académicos") y el precio.
Se rompe si: cambian las clases listadoActividades-* o actividad-* de las fichas. Sin Crawl-delay en su robots.txt."""
import html
import re
import time
from dataclasses import dataclass
from datetime import datetime

from app.scrapers.comun import (FuenteNoDisponible, guardar_sesiones, numero_mes, obtener_html, obtener_logger,
                                resolver_anio)

URL = "https://www.academiadecine.com/actividades/"
CINES = ["Academia de Cine"]
SALA = "Sala de proyecciones"
USER_AGENT = "fps24-bot (+https://fps24.es)"
PAUSA = 3  # segundos entre fichas, de cortesía
MAX_PETICIONES = 120  # listado + fichas; suele tener unas 60 actividades

log = obtener_logger(__name__)


@dataclass(frozen=True)
class Sesion:
    titulo: str
    fecha_hora: datetime
    precio: str
    link: str


def _texto(fragmento):
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", fragmento)).split())


def leer_listado(pagina):
    """HTML de /actividades/ -> [(url de la ficha, fecha_hora, título)]. Las que no se pueden fechar, con aviso."""
    actividades = []
    for bloque in pagina.split('<div class="listadoActividades-actividad"')[1:]:
        enlace = re.search(r'href="([^"]+)"', bloque)
        fecha = re.search(r'(?s)actividad-fecha">\s*(\d{1,2})/(\w+)\.?\s*·\s*(\d{1,2}):(\d{2})', bloque)
        titulo = re.search(r'(?s)actividad-nombre">(.*?)</h2>', bloque)
        try:
            if not (enlace and fecha and titulo):
                raise ValueError("faltan enlace, fecha o título")
            d, mes, h, m = int(fecha.group(1)), numero_mes(fecha.group(2)), int(fecha.group(3)), int(fecha.group(4))
            actividades.append((enlace.group(1), datetime(resolver_anio(mes, d), mes, d, h, m), _texto(titulo.group(1))))
        except ValueError as e:
            log.warning("Actividad descartada (%s): %r", e, _texto(bloque)[:120])
    return actividades


def leer_ficha(pagina):
    """HTML de una ficha -> su precio si es una película en la sala de Madrid abierta al público; si no, None.
    Precio: el de "público general" si lo da en euros ("3,15 €"); si no, el texto del bloque de entradas o "Consultar"."""
    sede = re.search(r'(?s)actividad-cabecera-subtitulo">(.*?)</div>\s*</div>', pagina)
    if not (sede and "sala de proyecciones" in _texto(sede.group(1)).lower()):
        return None  # Barcelona, el Café de la Academia...
    if "actividad-dato--formato" not in pagina:
        return None  # jornadas, talleres, encuentros: sin ficha técnica
    if re.search(r"exclusiv[oa]s? para (los miembros|acad[eé]micos)", html.unescape(pagina), re.I):
        return None  # pases solo para académicos: no hay entradas para el público
    # El bloque de entradas sale cuando abre la venta, unos días antes: hasta entonces, "Consultar"
    entradas = re.search(r'(?s)class="actividad-entradas-precio">(.*?)</div>', pagina)
    euros = re.search(r"(\d+)[’'.,](\d{2})\s*€\s*público general", html.unescape(pagina), re.I)
    if euros:
        return f"{euros.group(1)},{euros.group(2)} €"
    return (_texto(entradas.group(1)) if entradas else "") or "Consultar"


def leer_cine(contadores, obtener=lambda url: obtener_html(url, USER_AGENT), dormir=time.sleep):
    """Listado y una ficha por actividad (cada URL una vez), con PAUSA antes de cada ficha -> [Sesion]."""
    actividades = leer_listado(obtener(URL))
    contadores["peticiones"] = 1
    if not actividades:
        raise FuenteNoDisponible(f"{URL}: no hay actividades (¿ha cambiado la web?)")
    fichas = list(dict.fromkeys(url for url, _, _ in actividades))
    if 1 + len(fichas) > MAX_PETICIONES:
        raise FuenteNoDisponible(f"{URL}: {len(fichas)} fichas, más que el tope de {MAX_PETICIONES} peticiones")
    precios = {}
    for url in fichas:
        dormir(PAUSA)
        precios[url] = leer_ficha(obtener(url))
        contadores["peticiones"] += 1
        if precios[url] is None:
            contadores["descartado"] += 1
    return [Sesion(titulo, fecha_hora, precios[url], url) for url, fecha_hora, titulo in actividades if precios[url]]


def scrapear_academia_cine():
    contadores = {"creado": 0, "actualizado": 0, "descartado": 0, "peticiones": 0}
    return guardar_sesiones(CINES[0], leer_cine(contadores), SALA, contadores)


if __name__ == "__main__":
    scrapear_academia_cine()
