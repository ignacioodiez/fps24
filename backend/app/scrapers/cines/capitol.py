"""Lee: https://www.capitolgranvia.com/es/cine/ (HTML de servidor) -> la ficha /es/cartelera/<slug>/ de cada película.
Extrae: título del <h1>, versión del campo "Idioma" y, en section#comprar-entradas, un div data-tabs="AAAAMMDD" por día con un enlace admit-one por sesión ("15:45 (2D)").
Se rompe si: cambian las rutas /es/cartelera/, el id comprar-entradas, data-tabs o el campo Idioma. Su robots.txt pide Crawl-delay: 60 (PAUSA)."""
import html
import re
import time
from dataclasses import dataclass
from datetime import datetime

from sqlmodel import Session

from app.database.engine import engine
from app.scrapers.comun import FuenteNoDisponible, obtener_html, obtener_logger
from app.services.gestor_peliculas import resolver_pelicula
from app.services.pases import registrar_pase

URL = "https://www.capitolgranvia.com/es/cine/"
BASE = "https://www.capitolgranvia.com"
CINES = ["Cine Capitol Gran Vía"]
SALA = "Capitol Gran Vía"  # forma parte de la identidad del pase
PRECIO = "Consultar"
USER_AGENT = "fps24-bot (+https://fps24.es)"
PAUSA = 60  # segundos: el Crawl-delay de su robots.txt
MAX_PETICIONES = 15  # cartelera + fichas; suele tener 2-6 películas

log = obtener_logger(__name__)


@dataclass(frozen=True)
class Sesion:
    titulo: str
    fecha_hora: datetime
    idioma: str
    link: str


def leer_cartelera(pagina):
    """HTML de /es/cine/ -> URLs de las fichas, sin repetir y en orden."""
    return [BASE + r for r in dict.fromkeys(re.findall(r'href="(/es/cartelera/[^"/#?]+/)', pagina))]


def idioma_de(idioma, etiqueta=""):
    """Campo Idioma de la ficha ("ESPAÑOL") + texto de la sesión ("15:45 (2D)") -> 'VOSE' o 'Español'.
    VOSE si alguno dice V.O. o subtítulos, o si el idioma es otro que el español (la versión original)."""
    texto = f"{idioma} {etiqueta}".upper()
    if re.search(r"\bV\.?\s?O\b|V\.?O\.?S|SUBTITUL|ORIGINAL", texto):
        return "VOSE"
    return "Español" if not idioma.strip() or re.search(r"ESPAÑOL|CASTELLANO", idioma.upper()) else "VOSE"


def leer_ficha(pagina):
    """HTML de una ficha -> [Sesion]. Sin bloque de compra (aún sin sesiones): []. ValueError si no tiene título."""
    titulo = re.search(r"<h1>(.*?)</h1>", pagina, re.S)
    if not titulo:
        raise ValueError("ficha sin <h1>")
    titulo = html.unescape(re.sub(r"<[^>]+>", "", titulo.group(1))).strip()
    idioma = re.search(r"<small>Idioma</small>\s*<span>(.*?)</span>", pagina, re.S)
    idioma = html.unescape(idioma.group(1)).strip() if idioma else ""
    compra = re.search(r'(?s)id="comprar-entradas"(.*?)</section>', pagina)
    sesiones = []
    for dia in (compra.group(1).split('data-tabs="')[1:] if compra else []):
        fecha = re.match(r"(\d{4})(\d{2})(\d{2})\"", dia)
        if not fecha:
            continue
        a, m, d = map(int, fecha.groups())
        # Dentro del <a> va un <svg> (icono) antes del <span> con la hora
        for link, h, mi, resto in re.findall(r'(?s)<a href="([^"]+)"[^>]*>(?:(?!</a>).)*?<span>\s*(\d{1,2}):(\d{2})([^<]*)</span>', dia):
            try:
                sesiones.append(Sesion(titulo, datetime(a, m, d, int(h), int(mi)), idioma_de(idioma, resto),
                                       html.unescape(link)))
            except ValueError:
                log.warning("Pase descartado de %r: %s %s:%s", titulo, fecha.group(0), h, mi)
    return sesiones


def leer_cine(contadores, obtener=lambda url: obtener_html(url, USER_AGENT), dormir=time.sleep):
    """Cartelera y una ficha por película, con PAUSA antes de cada ficha -> [Sesion]."""
    fichas = leer_cartelera(obtener(URL))
    contadores["peticiones"] = 1
    if not fichas:
        raise FuenteNoDisponible(f"{URL}: no hay películas")
    if 1 + len(fichas) > MAX_PETICIONES:
        raise FuenteNoDisponible(f"{URL}: {len(fichas)} fichas, más que el tope de {MAX_PETICIONES} peticiones")
    sesiones = []
    for url in fichas:
        dormir(PAUSA)
        pagina = obtener(url)
        contadores["peticiones"] += 1
        try:
            sesiones += leer_ficha(pagina)
        except ValueError:
            log.warning("Ficha descartada: %s", url, exc_info=True)
            contadores["descartado"] += 1
    return sesiones


def scrapear_capitol():
    cine = CINES[0]
    contadores = {"creado": 0, "actualizado": 0, "descartado": 0, "peticiones": 0}
    peliculas = {}  # título de la web -> (pelicula_id, es_especial)

    with Session(engine) as session:
        sesiones = leer_cine(contadores)
        if not sesiones:
            raise FuenteNoDisponible(f"{URL}: no hay sesiones de {cine}")
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
                sala=SALA,
                idioma=s.idioma,
                precio=PRECIO,
                link_compra=s.link,
                es_evento_especial=es_especial,
            )
            contadores[resultado] += 1
        session.commit()
    log.info("%s: %s", cine, contadores)
    return contadores


if __name__ == "__main__":
    scrapear_capitol()
