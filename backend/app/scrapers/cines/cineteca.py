"""Lee: https://www.cinetecamadrid.com/programacion (solo la primera página del listado) y la ficha de cada película.
Extrae: un .node--type-activity por película con el enlace en h2.title a; en la ficha, .sb-sessions__items con h2 (mes), h4 ("Jueves 22") y ul (horas "19:30 h" y sala), y el año en .field--name-field-ano-filmacion (o el primero de .tit-ficha).
Se rompe si: cambian las clases del listado o de la ficha, o el formato "HH:MM h"; las fichas sin .sb-sessions__items se saltan."""
import re
from datetime import datetime

from playwright.sync_api import Error as PlaywrightError
from sqlmodel import Session

from app.database.engine import engine
from app.scrapers.comun import FuenteNoDisponible, abrir_pagina, numero_mes, obtener_logger, resolver_anio
from app.services.gestor_peliculas import resolver_pelicula
from app.services.pases import registrar_pase

BASE_URL = "https://www.cinetecamadrid.com"
URL = f"{BASE_URL}/programacion"
CINES = ["Cineteca"]
PRECIO = "3.50€"
IDIOMA = "VOSE"

log = obtener_logger(__name__)


def parsear_hora(texto):
    """'19:30 h' -> (19, 30). ValueError si no cuadra."""
    match = re.fullmatch(r"(\d{1,2}):(\d{2})\s*h?", texto.strip())
    if not match:
        raise ValueError(f"Hora no reconocida: {texto!r}")
    return int(match.group(1)), int(match.group(2))


def parsear_anio(texto):
    """Primer año 19xx/20xx del texto; None si no hay."""
    match = re.search(r"\b(?:19|20)\d{2}\b", texto)
    return int(match.group()) if match else None


def _leer_anio(page):
    """Campo de año de la ficha; si falta, el primer año que aparezca en la cabecera .tit-ficha."""
    campo = page.locator(".field--name-field-ano-filmacion")
    if campo.count():
        anio = parsear_anio(campo.first.inner_text())
        if anio:
            return anio
    cabecera = page.locator(".tit-ficha")
    return parsear_anio(cabecera.first.inner_text()) if cabecera.count() else None


def _leer_pases(bloque, titulo_raw, contadores):
    """Recorre h2 (mes) / h4 (día) / ul (horas y sala) en orden -> [(fecha_hora, sala)]."""
    pases = []
    mes = dia = None
    for elem in bloque.locator("> *").all():
        tag = elem.evaluate("el => el.tagName.toLowerCase()")
        texto = elem.inner_text().strip()
        try:
            if tag == "h2":
                mes = numero_mes(texto)
            elif tag == "h4":
                match = re.search(r"\d+", texto)
                if not match:
                    raise ValueError(f"Día no reconocido: {texto!r}")
                dia = int(match.group())
            elif tag == "ul":
                if mes is None or dia is None:
                    raise ValueError(f"Horas sin mes o día: {texto!r}")
                espacio = elem.locator("li.sb-sessions__date-hours-space")
                sala = espacio.first.inner_text().strip() if espacio.count() else "Cineteca"
                for li in elem.locator("li.sb-sessions__date-hours-hour").all():
                    h, m = parsear_hora(li.inner_text())
                    pases.append((datetime(resolver_anio(mes, dia), mes, dia, h, m), sala))
        except ValueError:
            log.warning("Pase descartado de %r: %r", titulo_raw, texto, exc_info=True)
            contadores["descartado"] += 1
    return pases


def _leer_ficha(session, page, link_ficha, cine, contadores):
    page.goto(link_ficha, wait_until="domcontentloaded")
    page.wait_for_selector("h2.title")
    titulo_raw = page.locator("h2.title").first.inner_text().strip()

    bloque = page.locator(".sb-sessions__items")
    if not bloque.count():
        log.info("%s: sin horarios en %r", cine, titulo_raw)
        return
    pases = _leer_pases(bloque.first, titulo_raw, contadores)
    if not pases:
        return

    pelicula_id, es_especial = resolver_pelicula(session, titulo_raw, cine, anio_web=_leer_anio(page))
    if pelicula_id is None:
        contadores["descartado"] += 1
        return

    for fecha_hora, sala in pases:
        resultado = registrar_pase(
            session,
            cine=cine,
            pelicula_id=pelicula_id,
            fecha_hora=fecha_hora,
            sala=sala,
            idioma=IDIOMA,
            precio=PRECIO,
            link_compra=link_ficha,
            es_evento_especial=es_especial,
        )
        contadores[resultado] += 1


def scrapear_cineteca():
    cine = CINES[0]
    contadores = {"creado": 0, "actualizado": 0, "descartado": 0}

    with abrir_pagina() as page, Session(engine) as session:
        page.goto(URL, wait_until="domcontentloaded")
        page.wait_for_selector(".node--type-activity")
        fichas = []
        for tarjeta in page.locator(".node--type-activity").all():
            enlace = tarjeta.locator("h2.title a").first
            href = enlace.get_attribute("href") if enlace.count() else None
            if not href:
                log.warning("%s: tarjeta sin enlace en %s", cine, URL)
                continue
            fichas.append(f"{BASE_URL}{href}")
        if not fichas:
            raise FuenteNoDisponible(f"{URL}: no hay películas")
        log.info("%s: %d fichas en la web", cine, len(fichas))

        for link in fichas:
            try:
                _leer_ficha(session, page, link, cine, contadores)
            except (ValueError, PlaywrightError):
                log.warning("Película descartada en %s: %s", cine, link, exc_info=True)
                contadores["descartado"] += 1

        session.commit()
    log.info("%s: %s", cine, contadores)


if __name__ == "__main__":
    scrapear_cineteca()
