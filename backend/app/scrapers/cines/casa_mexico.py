"""Lee: https://www.casademexico.es/tipo_actividad/cine-en-casa-de-mexico/ (WordPress) -> la ficha de cada actividad de cine.
Extrae: título del h1 (lo que va tras el último "|"), precio junto al icono precio.svg ("Gratis") y, en .sesiones-actividad,
un .bloque-sesion por pase ("19 de Noviembre de 2026", "19:00-21:00"); sin bloques, la .fecha de cabecera y la hora del icono
hora.svg. La ficha del ciclo entero ("Del ... al ...", "Múltiples sesiones") no tiene sesiones: se descarta.
Se rompe si: cambian esas clases, el icono del precio o la ruta del archivo. Sin Crawl-delay en su robots.txt."""
import html
import re
import time
from dataclasses import dataclass
from datetime import datetime

from app.scrapers.comun import FuenteNoDisponible, guardar_sesiones, numero_mes, obtener_html, obtener_logger

URL = "https://www.casademexico.es/tipo_actividad/cine-en-casa-de-mexico/"
CINES = ["Casa de México"]
SALA = "Cine-Auditorio"
USER_AGENT = "fps24-bot (+https://fps24.es)"
PAUSA = 3  # segundos entre fichas, de cortesía
MAX_PETICIONES = 40  # archivo + fichas; suele tener unas 13

log = obtener_logger(__name__)


@dataclass(frozen=True)
class Sesion:
    titulo: str
    fecha_hora: datetime
    precio: str
    link: str


def _texto(fragmento):
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", fragmento)).split())


def leer_archivo(pagina):
    """HTML del archivo -> URLs de las fichas, sin repetir y en orden. shortcut: solo la primera página del archivo
    (las más recientes, unas 13); si se quedan fuera sesiones futuras, seguir su paginación."""
    return list(dict.fromkeys(re.findall(r'href="(https://www\.casademexico\.es/cine-en-casa-de-mexico/[^"/#?]+/)"', pagina)))


def leer_ficha(pagina, url):
    """HTML de una ficha -> [Sesion]; [] si no tiene sesiones (la del ciclo). ValueError si no tiene título."""
    h1 = re.search(r"(?s)<h1[^>]*>(.*?)</h1>", pagina)
    if not h1:
        raise ValueError("ficha sin <h1>")
    titulo = _texto(h1.group(1)).rsplit("|", 1)[-1].strip()
    precio = re.search(r'(?s)precio\.svg.*?elementor-heading-title[^>]*>(.*?)</p>', pagina)
    precio = (_texto(precio.group(1)) if precio else "") or "Consultar"
    pares = [(re.search(r'fecha-sesion">\s*(\d{1,2}) de (\w+) de (\d{4})', b), re.search(r'class="hora">\s*(\d{1,2}):(\d{2})', b))
             for b in pagina.split('class="bloque-sesion"')[1:]]
    if not pares:
        # Sin bloque de sesiones (aún sin enlace de Eventbrite): la fecha de la cabecera (la primera .fecha; las demás son de
        # actividades relacionadas) y la hora junto al icono del reloj. La del ciclo ("Del 13 al 28...", "Múltiples
        # sesiones") no encaja y se queda sin sesiones.
        cabecera = re.search(r'class="fecha">([^<]*)<', pagina)
        reloj = re.search(r'(?s)hora\.svg"[^>]*>(.{0,1500})', pagina)
        fecha = cabecera and re.fullmatch(r"\s*(\d{1,2}) de (\w+) de (\d{4})\s*", cabecera.group(1))
        hora = reloj and re.match(r"\s*(\d{1,2}):(\d{2})\s*-", _texto(reloj.group(1)))
        pares = [(fecha, hora)] if fecha else []
    sesiones = []
    for fecha, hora in pares:
        try:
            if not (fecha and hora):
                raise ValueError("sesión sin fecha u hora")
            sesiones.append(Sesion(titulo, datetime(int(fecha.group(3)), numero_mes(fecha.group(2)), int(fecha.group(1)),
                                                    int(hora.group(1)), int(hora.group(2))), precio, url))
        except ValueError:
            log.warning("Sesión descartada de %r", titulo, exc_info=True)
    return sesiones


def leer_cine(contadores, obtener=lambda url: obtener_html(url, USER_AGENT), dormir=time.sleep):
    """Archivo y una ficha por actividad, con PAUSA antes de cada ficha -> [Sesion]."""
    fichas = leer_archivo(obtener(URL))
    contadores["peticiones"] = 1
    if not fichas:
        raise FuenteNoDisponible(f"{URL}: no hay fichas de cine (¿ha cambiado la web?)")
    if 1 + len(fichas) > MAX_PETICIONES:
        raise FuenteNoDisponible(f"{URL}: {len(fichas)} fichas, más que el tope de {MAX_PETICIONES} peticiones")
    sesiones = []
    for url in fichas:
        dormir(PAUSA)
        pagina = obtener(url)
        contadores["peticiones"] += 1
        try:
            de_la_ficha = leer_ficha(pagina, url)
        except ValueError:
            log.warning("Ficha descartada: %s", url, exc_info=True)
            de_la_ficha = []
        if not de_la_ficha:
            contadores["descartado"] += 1  # la del ciclo entero o una sin sesiones
        sesiones += de_la_ficha
    return sesiones


def scrapear_casa_mexico():
    contadores = {"creado": 0, "actualizado": 0, "descartado": 0, "peticiones": 0}
    return guardar_sesiones(CINES[0], leer_cine(contadores), SALA, contadores)


if __name__ == "__main__":
    scrapear_casa_mexico()
