"""Lee: https://www.cinepazmadrid.es/es/cartelera (plantilla mk2, ver app/scrapers/plataforma_mk2.py); todos los días están ya en el HTML.
Extrae: las 7 primeras pestañas .rotulo_dia ("Hoy", "Mañana", "Sábado 24/10"); en .cines-<data-num>, un .horarios por película con el título en .text-header-span a, .etiqueta-vose y las horas en .horas .btn.metrica ("35mm15:45").
Se rompe si: cambian las clases de la plantilla o el texto de las pestañas; los botones sin HH:MM se descartan con aviso."""
from datetime import datetime, time

from playwright.sync_api import Error as PlaywrightError
from sqlmodel import Session

from app.database.engine import engine
from app.scrapers.comun import FuenteNoDisponible, abrir_pagina, obtener_logger
from app.scrapers.plataforma_mk2 import leer_dias, parsear_hora
from app.services.gestor_peliculas import resolver_pelicula
from app.services.pases import registrar_pase

URL = "https://www.cinepazmadrid.es/es/cartelera"
CINES = ["Cine MK2 Paz"]
SALA = "Cine Paz"
PRECIO = "Consultar"
MAX_DIAS = 7

log = obtener_logger(__name__)


def idioma_de(titulo_raw, tiene_etiqueta_vose):
    """VOSE si la web pone la etiqueta o el título lo dice ("(VOSE)", "V.O.S.E"); si no, Español."""
    titulo = titulo_raw.upper()
    return "VOSE" if tiene_etiqueta_vose or "VOSE" in titulo or "V.O.S.E" in titulo else "Español"


def _leer_pelicula(session, peli, fecha, cine, peliculas, contadores):
    titulo = peli.locator(".peli .text-header-span a").first
    if not titulo.count():
        log.warning("%s: película sin título el %s", cine, fecha)
        contadores["descartado"] += 1
        return
    titulo_raw = titulo.inner_text().strip()
    if titulo_raw not in peliculas:  # la misma película sale en varios días: se resuelve una vez
        peliculas[titulo_raw] = resolver_pelicula(session, titulo_raw, cine)
    pelicula_id, es_especial = peliculas[titulo_raw]
    if pelicula_id is None:
        contadores["descartado"] += 1
        return

    idioma = idioma_de(titulo_raw, peli.locator(".etiqueta-vose").count() > 0)
    for boton in peli.locator(".horas .btn.metrica").all():
        hora_txt = boton.inner_text().strip()
        try:
            fecha_hora = datetime.combine(fecha, time(*parsear_hora(hora_txt)))
        except ValueError:
            log.warning("Pase descartado de %r: %s %r", titulo_raw, fecha, hora_txt, exc_info=True)
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


def scrapear_cine_paz():
    cine = CINES[0]
    contadores = {"creado": 0, "actualizado": 0, "descartado": 0}
    peliculas = {}  # título de la web -> (pelicula_id, es_especial)
    leidas = 0

    with abrir_pagina() as page, Session(engine) as session:
        page.goto(URL, wait_until="domcontentloaded")
        page.locator(".contenedor_cines .horarios").first.wait_for(state="attached")
        dias = leer_dias(page, cine, MAX_DIAS)
        log.info("%s: %d días a leer", cine, len(dias))

        for data_num, fecha in dias:
            for peli in page.locator(f".contenedor_cines.cines-{data_num} .horarios").all():
                leidas += 1
                try:
                    _leer_pelicula(session, peli, fecha, cine, peliculas, contadores)
                except PlaywrightError:
                    log.warning("Película descartada en %s el %s", cine, fecha, exc_info=True)
                    contadores["descartado"] += 1

        if not leidas:
            raise FuenteNoDisponible(f"{URL}: no hay películas en {len(dias)} días")
        session.commit()
    log.info("%s: %s", cine, contadores)


if __name__ == "__main__":
    scrapear_cine_paz()
