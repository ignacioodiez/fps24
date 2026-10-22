"""Lee: https://madrid.cines-verdi.com/cartelera (web con Alpine.js; las sesiones de cada película cargan al verla en pantalla).
Extrae: un article por película; por cada fecha de select.dates-select, los .button-buy visibles (hora en <time>, versión en data-attr).
Se rompe si: cambian las clases, el select o el formato YYYY-MM-DD; los pases agotados o sin enlace ("#") se saltan y desaparecen."""
import os
import re
import tempfile
from datetime import datetime

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from sqlmodel import Session

from app.database.engine import engine
from app.scrapers.comun import FuenteNoDisponible, abrir_pagina, obtener_logger
from app.services.gestor_peliculas import resolver_pelicula
from app.services.pases import registrar_pase

URL = "https://madrid.cines-verdi.com/cartelera"
CINES = ["Cines Verdi"]
PRECIO = "Consultar"

log = obtener_logger(__name__)


def scrapear_verdi():
    cine = CINES[0]
    contadores = {"creado": 0, "actualizado": 0, "descartado": 0}

    with abrir_pagina() as page, Session(engine) as session:
        page.goto(URL, wait_until="domcontentloaded")
        try:
            page.wait_for_selector(".collection article")
        except PlaywrightError:
            if os.environ.get("SCRAPERS_DEBUG") == "1":
                page.screenshot(path=os.path.join(tempfile.gettempdir(), "debug_verdi.png"))
            raise
        articles = page.locator(".collection article").all()
        if not articles:
            raise FuenteNoDisponible(f"{URL}: no hay películas")
        log.info("%s: %d películas en la web", cine, len(articles))

        for article in articles:
            raw_titulo = None
            try:
                titulo_elem = article.locator(".syn header h2").first
                if not titulo_elem.count():
                    titulo_elem = article.locator("figcaption h2").first
                if not titulo_elem.count():
                    log.warning("Película sin título en %s", cine)
                    contadores["descartado"] += 1
                    continue
                raw_titulo = titulo_elem.inner_text().strip()

                # Las sesiones se cargan al entrar en pantalla (x-intersect): select de fechas o aviso de sin entradas
                article.scroll_into_view_if_needed()
                try:
                    article.locator("select.dates-select, [role=alert]").first.wait_for(state="attached")
                except PlaywrightTimeoutError:
                    log.warning("No cargan las sesiones de %r en %s", raw_titulo, cine)
                    contadores["descartado"] += 1
                    continue

                pelicula_id, es_especial = resolver_pelicula(session, raw_titulo, cine)
                if pelicula_id is None:
                    contadores["descartado"] += 1
                    continue

                fechas = {}  # value (YYYY-MM-DD) -> texto de la opción, en orden
                for op in article.locator("select.dates-select option").all():
                    val = op.get_attribute("value")
                    if val:
                        fechas.setdefault(val, op.text_content().strip())
                if not fechas:
                    log.info("Sin fechas a la venta para %r", raw_titulo)
                    continue

                for fecha_str, texto_opcion in fechas.items():
                    article.locator("select.dates-select").select_option(value=fecha_str, force=True)
                    # La etiqueta y los x-show de los pases se actualizan en el mismo ciclo de Alpine
                    article.locator(".nowplaying-selector span",
                                    has_text=re.compile(f"^{re.escape(texto_opcion)}$")).wait_for(state="attached")

                    for pase in article.locator(".info-performances .button-buy").all():
                        if not pase.is_visible():
                            continue  # pase de otra fecha, oculto por Alpine
                        link_compra = pase.get_attribute("href")
                        if not link_compra or link_compra == "#":
                            continue  # agotado o sin enlace
                        hora_txt = None
                        try:
                            hora_txt = pase.locator("time").inner_text().strip()
                            version_attr = (pase.get_attribute("data-attr") or "").upper()
                            resultado = registrar_pase(
                                session,
                                cine=cine,
                                pelicula_id=pelicula_id,
                                fecha_hora=datetime.strptime(f"{fecha_str} {hora_txt}", "%Y-%m-%d %H:%M"),
                                sala=cine,
                                idioma="VOSE" if "V.O." in version_attr or "SUB" in version_attr else "Español",
                                precio=PRECIO,
                                link_compra=link_compra,
                                es_evento_especial=es_especial,
                            )
                            contadores[resultado] += 1
                        except (ValueError, PlaywrightError):
                            log.warning("Pase descartado de %r: %s %r", raw_titulo, fecha_str, hora_txt, exc_info=True)
                            contadores["descartado"] += 1

            except (ValueError, PlaywrightError):
                log.warning("Película descartada en %s: %r", cine, raw_titulo, exc_info=True)
                contadores["descartado"] += 1

        session.commit()
    log.info("%s: %s", cine, contadores)


if __name__ == "__main__":
    scrapear_verdi()
