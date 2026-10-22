"""Lee: https://www.circulobellasartes.com/ciclos-cine/ (listado del Círculo de Bellas Artes) y la ficha de cada película.
Extrae: un .fl-post-grid-post por película con el enlace en .carousel-item-titulo a; en la ficha, una fila de table.cba_tabla_sesiones por pase ("Dom 25/10, 17:00"), el año en la fila "Año" de la ficha técnica y el botón de compra a.fl-button.
Se rompe si: cambian las clases del listado o de la tabla, o el formato "dd/mm, HH:MM"; las fichas de ciclo sin tabla de sesiones se saltan."""
import re
from datetime import datetime

from playwright.sync_api import Error as PlaywrightError
from sqlmodel import Session

from app.database.engine import engine
from app.scrapers.comun import FuenteNoDisponible, abrir_pagina, hoy_madrid, obtener_logger, resolver_anio
from app.services.gestor_peliculas import resolver_pelicula
from app.services.pases import registrar_pase

URL = "https://www.circulobellasartes.com/ciclos-cine/"
CINES = ["Cine Estudio (CBA)"]
SALA = "Sala Cine Estudio"
PRECIO = "5.50€"
IDIOMA = "VOSE"

log = obtener_logger(__name__)


def parsear_fecha_hora(texto):
    """'Dom 25/10, 17:00' -> datetime. ValueError si no cuadra."""
    match = re.search(r"(\d{1,2})/(\d{1,2}).*?(\d{1,2}):(\d{2})", texto)
    if not match:
        raise ValueError(f"Fecha no reconocida: {texto!r}")
    dia, mes, h, m = map(int, match.groups())
    return datetime(resolver_anio(mes, dia), mes, dia, h, m)


def _leer_anio(page):
    """Fila "Año | 2026" de la ficha técnica; None si no está."""
    fila = page.locator("tr", has=page.locator("td", has_text=re.compile(r"^\s*Año\s*$")))
    if not fila.count():
        return None
    match = re.search(r"\d{4}", fila.first.locator("td").nth(1).inner_text())
    return int(match.group()) if match else None


def _leer_ficha(session, page, titulo_raw, link_ficha, cine, contadores):
    page.goto(link_ficha, wait_until="domcontentloaded")
    filas = page.locator("table.cba_tabla_sesiones tr td:first-child").all()
    if not filas:
        # Fichas de ciclo o festival: no se resuelven para no crear películas basura
        log.info("%s: sin sesiones en %r", cine, titulo_raw)
        return

    hoy = hoy_madrid()
    pases = []
    for celda in filas:
        texto = celda.inner_text().strip()
        try:
            fecha_hora = parsear_fecha_hora(texto)
        except ValueError:
            log.warning("Pase descartado de %r: %r", titulo_raw, texto, exc_info=True)
            contadores["descartado"] += 1
            continue
        if fecha_hora.date() >= hoy:  # la ficha sigue mostrando los pases ya pasados
            pases.append(fecha_hora)
    if not pases:
        return

    pelicula_id, es_especial = resolver_pelicula(session, titulo_raw, cine, anio_web=_leer_anio(page))
    if pelicula_id is None:
        contadores["descartado"] += 1
        return

    boton = page.locator("a.fl-button[href*='reservaentradas'], a.fl-button[href*='tickets']").first
    link_compra = (boton.get_attribute("href") if boton.count() else None) or link_ficha
    for fecha_hora in pases:
        resultado = registrar_pase(
            session,
            cine=cine,
            pelicula_id=pelicula_id,
            fecha_hora=fecha_hora,
            sala=SALA,
            idioma=IDIOMA,
            precio=PRECIO,
            link_compra=link_compra,
            es_evento_especial=es_especial,
        )
        contadores[resultado] += 1


def scrapear_cine_estudio():
    cine = CINES[0]
    contadores = {"creado": 0, "actualizado": 0, "descartado": 0}

    with abrir_pagina() as page, Session(engine) as session:
        page.goto(URL, wait_until="domcontentloaded")
        page.wait_for_selector(".fl-post-grid-post")
        fichas = []
        for post in page.locator(".fl-post-grid-post").all():
            titulo_el = post.locator(".carousel-item-titulo a").first
            if not titulo_el.count():
                log.warning("%s: tarjeta sin título en %s", cine, URL)
                continue
            link = titulo_el.get_attribute("href")
            if link:
                fichas.append((titulo_el.inner_text().strip(), link))
        if not fichas:
            raise FuenteNoDisponible(f"{URL}: no hay películas")
        log.info("%s: %d fichas en la web", cine, len(fichas))

        for titulo_raw, link in fichas:
            try:
                _leer_ficha(session, page, titulo_raw, link, cine, contadores)
            except (ValueError, PlaywrightError):
                log.warning("Película descartada en %s: %r", cine, titulo_raw, exc_info=True)
                contadores["descartado"] += 1

        session.commit()
    log.info("%s: %s", cine, contadores)


if __name__ == "__main__":
    scrapear_cine_estudio()
