"""Lee: https://www.yelmocines.es/cartelera/madrid (cartelera de Madrid; la web pinta cada fecha en el navegador al cambiar #ddlDate, sin pedir nada a la red).
Extrae: por cada uno de los 7 primeros valores de #ddlDate ("22-octubre"), los article.now__movie de div[data-cinema=ideal]; formato en .horarioExp .col3 y horas/enlaces en time.btn a.
Se rompe si: Cloudflare bloquea el navegador (403 "Attention Required"), cambian las clases, el id del select o el formato "DD-mes"."""
import re
from datetime import datetime

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from sqlmodel import Session

from app.database.engine import engine
from app.scrapers.comun import FuenteNoDisponible, abrir_pagina, numero_mes, obtener_logger, resolver_anio
from app.services.gestor_peliculas import resolver_pelicula
from app.services.pases import registrar_pase

URL = "https://www.yelmocines.es/cartelera/madrid"
CINES = ["Yelmo Cines Ideal"]
SALA = "Yelmo Ideal"
PRECIO = "Consultar"
DIAS = 7

log = obtener_logger(__name__)


def parsear_fecha(valor, hora_txt):
    """('22-octubre', '15:45') -> datetime. ValueError si no cuadra."""
    dia, mes_txt = valor.split("-")
    dia, mes = int(dia), numero_mes(mes_txt)
    h, m = map(int, hora_txt.split(":"))
    return datetime(resolver_anio(mes, dia), mes, dia, h, m)


def idioma_de(formato):
    """'2D INGLÉS SUBTITULADO EN ESPAÑOL (VOSE)' -> 'VOSE'; el resto, 'Español'."""
    formato = formato.upper()
    return "VOSE" if "VOSE" in formato or "SUBTITULADO" in formato else "Español"


def _abrir_cartelera(page):
    respuesta = page.goto(URL, wait_until="domcontentloaded")
    if (respuesta and respuesta.status == 403) or "Attention Required" in page.title():
        raise FuenteNoDisponible(f"Yelmo: bloqueado por Cloudflare (HTTP {respuesta.status if respuesta else '?'}) en {URL}")
    try:
        page.locator("#CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll").click(timeout=5000)
    except PlaywrightTimeoutError:
        log.info("Yelmo: sin banner de cookies")
    page.wait_for_function("document.querySelectorAll('#ddlDate option').length > 1")
    return [v for v in page.locator("#ddlDate option").evaluate_all("os => os.map(o => o.value)") if v != "0"][:DIAS]


def _leer_pelicula(session, peli, valor, cine, peliculas, contadores):
    titulo = peli.locator("header h3 a").first
    if not titulo.count():
        log.warning("%s: película sin título el %s", cine, valor)
        contadores["descartado"] += 1
        return
    titulo_raw = titulo.inner_text().strip()
    if titulo_raw not in peliculas:  # la misma película sale en varios días: se resuelve una vez
        peliculas[titulo_raw] = resolver_pelicula(session, titulo_raw, cine)
    pelicula_id, es_especial = peliculas[titulo_raw]
    if pelicula_id is None:
        contadores["descartado"] += 1
        return

    for bloque in peli.locator(".horarioExp").all():
        idioma = idioma_de(bloque.locator(".col3").inner_text())
        for boton in bloque.locator("time.btn a").all():
            hora_txt = boton.inner_text().strip()
            try:
                fecha_hora = parsear_fecha(valor, hora_txt)
            except ValueError:
                log.warning("Pase descartado de %r: %s %r", titulo_raw, valor, hora_txt, exc_info=True)
                contadores["descartado"] += 1
                continue
            resultado = registrar_pase(
                session,
                cine=cine,
                pelicula_id=pelicula_id,
                fecha_hora=fecha_hora,
                sala=SALA,
                idioma=idioma,
                precio=PRECIO,
                link_compra=boton.get_attribute("href"),
                es_evento_especial=es_especial,
            )
            contadores[resultado] += 1


def scrapear_yelmo_ideal():
    cine = CINES[0]
    contadores = {"creado": 0, "actualizado": 0, "descartado": 0}
    peliculas = {}  # título de la web -> (pelicula_id, es_especial)
    leidas = 0

    with abrir_pagina(navegacion_ms=90_000) as page, Session(engine) as session:
        fechas = _abrir_cartelera(page)
        log.info("%s: %d fechas a leer", cine, len(fechas))
        for valor in fechas:
            texto = page.locator(f"#ddlDate option[value='{valor}']").inner_text().strip()
            page.select_option("#ddlDate", value=valor, force=True)
            # El cambio pinta la cartelera y luego actualiza la etiqueta del select, en el mismo evento
            page.locator("#uniform-ddlDate span", has_text=re.compile(rf"^{re.escape(texto)}$")).wait_for()

            contenedor = page.locator('div[data-cinema="ideal"]')
            if not contenedor.count():
                log.info("%s: sin cartelera el %s", cine, valor)
                continue
            contenedor.first.evaluate("e => e.style.display = 'block'")
            for peli in contenedor.first.locator("article.now__movie").all():
                leidas += 1
                try:
                    _leer_pelicula(session, peli, valor, cine, peliculas, contadores)
                except PlaywrightError:
                    log.warning("Película descartada en %s el %s", cine, valor, exc_info=True)
                    contadores["descartado"] += 1

        if not leidas:
            raise FuenteNoDisponible(f"{URL}: no hay películas de {cine} en {len(fechas)} fechas")
        session.commit()
    log.info("%s: %s", cine, contadores)


if __name__ == "__main__":
    scrapear_yelmo_ideal()
