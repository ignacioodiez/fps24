"""Lee: https://www.golem.es/golem/golem-madrid (hoy) y /golem-madrid/AAAAMMDD para los días siguientes, una página por día.
Extrae: una table[background="#AEAEAE"] por película, título en .txtNegXXL ("Naza (V.O.S.E.)") y una .CajaVentasSup por sesión ("HH:MM" con enlace de compra).
Se rompe si: cambian el atributo background de las tablas, las clases .txtNegXXL / .CajaVentasSup o la URL por fecha; los bloques de ciclos (sin horas) se saltan."""
from datetime import datetime, timedelta

from playwright.sync_api import Error as PlaywrightError
from sqlmodel import Session

from app.database.engine import engine
from app.scrapers.comun import FuenteNoDisponible, abrir_pagina, hoy_madrid, obtener_logger
from app.services.gestor_peliculas import resolver_pelicula
from app.services.pases import registrar_pase

URL = "https://www.golem.es/golem/golem-madrid"
CINES = ["Golem Madrid"]
SALA = "Golem Madrid"
PRECIO = "Consultar"
DIAS_A_ESCANEAR = 7

log = obtener_logger(__name__)


def idioma_de(titulo_raw):
    return "VOSE" if "(V.O.S.E.)" in titulo_raw or "(VOSE)" in titulo_raw else "Español"


def _leer_bloque(session, bloque, fecha, cine, contadores):
    titulo_elem = bloque.locator(".txtNegXXL").first
    if not titulo_elem.count():
        return
    titulo_raw = titulo_elem.inner_text().strip()
    # Los bloques de ciclos no tienen horas: no se resuelven para no crear películas basura
    sesiones = [(c, t) for c in bloque.locator(".CajaVentasSup").all() if ":" in (t := c.inner_text().strip())]
    if not sesiones:
        return
    pelicula_id, es_especial = resolver_pelicula(session, titulo_raw, cine)
    if pelicula_id is None:
        contadores["descartado"] += 1
        return

    for celda, hora_txt in sesiones:
        try:
            h, m = map(int, hora_txt.split(":"))
            link = celda.locator("a").first
            href = link.get_attribute("href") if link.count() else None
            resultado = registrar_pase(
                session,
                cine=cine,
                pelicula_id=pelicula_id,
                fecha_hora=datetime(fecha.year, fecha.month, fecha.day, h, m),
                sala=SALA,
                idioma=idioma_de(titulo_raw),
                precio=PRECIO,
                link_compra=f"https://www.golem.es{href}" if href else URL,
                es_evento_especial=es_especial,
            )
            contadores[resultado] += 1
        except (ValueError, PlaywrightError):
            log.warning("Pase descartado de %r el %s: %r", titulo_raw, fecha, hora_txt, exc_info=True)
            contadores["descartado"] += 1


def scrapear_golem():
    cine = CINES[0]
    contadores = {"creado": 0, "actualizado": 0, "descartado": 0}
    hoy = hoy_madrid()

    with abrir_pagina() as page, Session(engine) as session:
        for i in range(DIAS_A_ESCANEAR):
            fecha = hoy + timedelta(days=i)
            url = URL if i == 0 else f"{URL}/{fecha:%Y%m%d}"
            page.goto(url, wait_until="domcontentloaded")  # si no carga, Playwright lanza la excepción
            bloques = page.locator('table[background="#AEAEAE"]').all()
            if not bloques:
                if i == 0:
                    raise FuenteNoDisponible(f"{url}: no hay películas")
                log.info("%s: sin películas el %s", cine, fecha)
                continue
            for bloque in bloques:
                try:
                    _leer_bloque(session, bloque, fecha, cine, contadores)
                except (ValueError, PlaywrightError):
                    log.warning("Película descartada en %s el %s", cine, fecha, exc_info=True)
                    contadores["descartado"] += 1

        session.commit()
    log.info("%s: %s", cine, contadores)


if __name__ == "__main__":
    scrapear_golem()
