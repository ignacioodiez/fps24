"""Lee: https://cinesembajadores.es/madrid/ (una sola página con la cartelera de las dos sedes, Embajadores y Embajadores Río).
Extrae: un li.movie por película, título en .info h2 a ("Naza (VOSE)") y un p[data-dia] por pase con data-dia "dd/mm", data-hora "HH:MM", data-recinto (sede) y a.compraTicket.
Se rompe si: cambian las clases o los atributos data-*, o el texto de data-recinto deja de contener "Río"/"Rio" para la segunda sede."""
from datetime import datetime

from playwright.sync_api import Error as PlaywrightError
from sqlmodel import Session

from app.database.engine import engine
from app.scrapers.comun import FuenteNoDisponible, abrir_pagina, obtener_logger, resolver_anio
from app.services.gestor_peliculas import resolver_pelicula
from app.services.pases import registrar_pase

URL = "https://cinesembajadores.es/madrid/"
CINES = ["Cine Embajadores", "Cine Embajadores Río"]
PRECIO = "Consultar"

log = obtener_logger(__name__)


def cine_de(recinto):
    """data-recinto ("Cines Embajadores", "Cine Embajadores Río") -> nombre de CINES."""
    return CINES[1] if "Río" in recinto or "Rio" in recinto else CINES[0]


def parsear_fecha_hora(dia_txt, hora_txt):
    """'23/10', '17:30' -> datetime. ValueError si no cuadra."""
    dia, mes = map(int, dia_txt.split("/"))
    h, m = map(int, hora_txt.split(":"))
    return datetime(resolver_anio(mes, dia), mes, dia, h, m)


def _leer_pelicula(session, peli_card, contadores):
    titulo_elem = peli_card.locator(".info h2 a").first
    if not titulo_elem.count():
        log.warning("Película sin título en %s", URL)
        contadores["descartado"] += 1
        return
    titulo_raw = titulo_elem.inner_text().strip()
    idioma = "VOSE" if "(VOSE)" in titulo_raw.upper() else "Español"
    pelicula_id = None

    for item in peli_card.locator(".showtimelist p[data-dia]").all():
        dia_txt = hora_txt = None
        try:
            dia_txt, hora_txt = item.get_attribute("data-dia"), item.get_attribute("data-hora")
            cine = cine_de(item.get_attribute("data-recinto") or "")
            fecha_hora = parsear_fecha_hora(dia_txt, hora_txt)
            if pelicula_id is None:
                # El cine solo sirve para el log: la película es la misma en las dos sedes
                pelicula_id, es_especial = resolver_pelicula(session, titulo_raw, cine)
                if pelicula_id is None:
                    contadores["descartado"] += 1
                    return
            link = item.locator("a.compraTicket").first
            resultado = registrar_pase(
                session,
                cine=cine,
                pelicula_id=pelicula_id,
                fecha_hora=fecha_hora,
                sala=cine,  # el nombre del cine como sala genérica
                idioma=idioma,
                precio=PRECIO,
                link_compra=link.get_attribute("href") if link.count() else URL,
                es_evento_especial=es_especial,
            )
            contadores[resultado] += 1
        except (ValueError, PlaywrightError):
            log.warning("Pase descartado de %r: %r %r", titulo_raw, dia_txt, hora_txt, exc_info=True)
            contadores["descartado"] += 1


def scrapear_embajadores():
    contadores = {"creado": 0, "actualizado": 0, "descartado": 0}

    with abrir_pagina() as page, Session(engine) as session:
        page.goto(URL, wait_until="domcontentloaded")
        page.wait_for_selector("ul.cartelera li.movie")
        peliculas = page.locator("ul.cartelera li.movie").all()
        if not peliculas:
            raise FuenteNoDisponible(f"{URL}: no hay películas")
        log.info("%s: %d películas en la web", " / ".join(CINES), len(peliculas))

        for peli_card in peliculas:
            try:
                _leer_pelicula(session, peli_card, contadores)
            except (ValueError, PlaywrightError):
                log.warning("Película descartada en %s", URL, exc_info=True)
                contadores["descartado"] += 1

        session.commit()
    log.info("%s: %s", " / ".join(CINES), contadores)


if __name__ == "__main__":
    scrapear_embajadores()
