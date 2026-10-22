"""Lee: https://www.mk2palaciodehielo.es/es/cartelera (plantilla mk2, ver app/scrapers/plataforma_mk2.py); solo el día visible (hoy), aunque el HTML trae más.
Extrae: en el .cines-<data-num> visible, un .horarios por película con el título en p.gibsonT b, .etiqueta-vose y las horas en .horas a.btn ("VOSE19:00").
Se rompe si: cambian las clases de la plantilla; los botones con otra etiqueta ("Directo19:00", "TEATRO EN VIVO19:00") se descartan con aviso."""
from datetime import datetime, time

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from sqlmodel import Session

from app.database.engine import engine
from app.scrapers.comun import FuenteNoDisponible, abrir_pagina, obtener_logger
from app.scrapers.plataforma_mk2 import leer_dias
from app.services.gestor_peliculas import resolver_pelicula
from app.services.pases import registrar_pase

URL = "https://www.mk2palaciodehielo.es/es/cartelera"
CINES = ["Mk2 Palacio de Hielo"]
SALA = "Mk2 Palacio de Hielo"
PRECIO = "Consultar"
MAX_DIAS = 7

log = obtener_logger(__name__)


def parsear_hora(texto):
    """'19:00' o 'VOSE19:00' -> (19, 0); con cualquier otra etiqueta, ValueError."""
    h, m = texto.replace("VOSE", "").strip().split(":")
    return int(h), int(m)


def idioma_de(titulo_raw, tiene_etiqueta_vose):
    """VOSE si el título lleva "(VOSE)" o la web pone .etiqueta-vose; si no, Español."""
    return "VOSE" if "(VOSE)" in titulo_raw.upper() or tiene_etiqueta_vose else "Español"


def _leer_pelicula(session, bloque, fecha, cine, contadores):
    titulo = bloque.locator("p.gibsonT b").first
    if not titulo.count():
        log.warning("%s: película sin título el %s", cine, fecha)
        contadores["descartado"] += 1
        return
    titulo_raw = titulo.inner_text().strip()
    pelicula_id, es_especial = resolver_pelicula(session, titulo_raw, cine)
    if pelicula_id is None:
        contadores["descartado"] += 1
        return

    idioma = idioma_de(titulo_raw, bloque.locator(".etiqueta-vose").count() > 0)
    for boton in bloque.locator(".horas a.btn").all():
        hora_txt = boton.inner_text().strip()
        try:
            fecha_hora = datetime.combine(fecha, time(*parsear_hora(hora_txt)))
        except ValueError:
            log.warning("Pase descartado de %r: %s %r", titulo_raw, fecha, hora_txt)
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


def scrapear_mk2_palacio_hielo():
    cine = CINES[0]
    contadores = {"creado": 0, "actualizado": 0, "descartado": 0}
    leidas = 0

    with abrir_pagina() as page, Session(engine) as session:
        page.goto(URL, wait_until="domcontentloaded")
        try:
            page.get_by_text("ACEPTAR", exact=True).click(timeout=3000)
        except PlaywrightTimeoutError:
            log.info("%s: sin banner de cookies", cine)
        page.locator(".contenedor_cines .horarios").first.wait_for(state="attached")

        for data_num, fecha in leer_dias(page, cine, MAX_DIAS):
            contenedor = page.locator(f".cines-{data_num}")
            # shortcut: solo el día visible (hoy), como la versión anterior; para leer los 7 días, quitar este if
            if not contenedor.is_visible():
                continue
            for bloque in contenedor.locator(".horarios").all():
                leidas += 1
                try:
                    _leer_pelicula(session, bloque, fecha, cine, contadores)
                except PlaywrightError:
                    log.warning("Película descartada en %s el %s", cine, fecha, exc_info=True)
                    contadores["descartado"] += 1

        if not leidas:
            raise FuenteNoDisponible(f"{URL}: no hay películas en el día visible")
        session.commit()
    log.info("%s: %s", cine, contadores)


if __name__ == "__main__":
    scrapear_mk2_palacio_hielo()
