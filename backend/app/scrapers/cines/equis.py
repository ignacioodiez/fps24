"""Lee: https://salaequis.es/taquilla/ -> ficha de una película -> taquilla de Kinetike (ASP.NET), que tras "Volver" muestra la cartelera día a día.
Extrae: por cada día (#lblContFecha "dd/mm/aaaa", avanzando con #imgSiguiente), un .panel_peli por película con título en .info_negrita y un <a> por sesión ("HH:MM").
Se rompe si: la primera ficha de salaequis.es deja de enlazar a Kinetike, cambian los ids ctl07/#lblContFecha/#imgSiguiente o el postback de los enlaces."""
import re
from datetime import datetime, timedelta

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import expect
from sqlmodel import Session

from app.database.engine import engine
from app.scrapers.comun import FuenteNoDisponible, abrir_pagina, obtener_logger
from app.services.gestor_peliculas import resolver_pelicula
from app.services.pases import registrar_pase

URL = "https://salaequis.es/taquilla/"
CINES = ["Sala Equis"]
SALA = "Sala Equis"
PRECIO = "6.90€"
IDIOMA = "VOSE"  # Sala Equis casi siempre es VOSE
DIAS_A_ESCANEAR = 7
KINETIKE = "https://kinetike.com:83/views/"

log = obtener_logger(__name__)


def parsear_link(href):
    """Postback de Kinetike -> URL directa de numEntradas.aspx; si no lo reconoce, el href tal cual."""
    href = href or ""
    if "javascript" in href and "numEntradas.aspx" in href:
        match = re.search(r'"(numEntradas\.aspx.*?)"', href)
        if match:
            return KINETIKE + match.group(1)
    elif href and not href.startswith("http"):
        return KINETIKE + href
    return href


def _entrar_en_kinetike(page):
    page.goto(URL)
    entrada = page.locator(".buy.bigFont a").first
    if not entrada.count():
        raise FuenteNoDisponible(f"{URL}: sin enlaces de entrada")
    page.goto(entrada.get_attribute("href"))
    kinetike = page.locator("a[href*='kinetike.com']").first
    if not kinetike.count():
        raise FuenteNoDisponible(f"{page.url}: sin enlace a Kinetike")
    page.goto(kinetike.get_attribute("href"))
    # "Volver" pasa de la ficha a la cartelera completa; pide confirmación con un diálogo
    page.on("dialog", lambda dialog: dialog.accept())
    if page.locator('input[name="ctl07"]').is_visible():
        page.locator('input[name="ctl07"]').click()
    page.wait_for_selector("#UpdatePanelFechas")


def _leer_dia(session, page, fecha, cine, contadores):
    for tarjeta in page.locator(".panel_peli").all():
        titulo_raw = None
        try:
            titulo_raw = tarjeta.locator(".info_negrita").first.inner_text().strip()
            # La cartelera lista todas las películas cada día; solo las del día llevan enlaces de sesión
            sesiones = [(m, a) for a in tarjeta.locator("a").all()
                        if (m := re.search(r"(\d{2}):(\d{2})", a.inner_text()))]
            if not sesiones:
                continue
            pelicula_id, es_especial = resolver_pelicula(session, titulo_raw, cine)
            if pelicula_id is None:
                contadores["descartado"] += 1
                continue
            for match, enlace in sesiones:
                resultado = registrar_pase(
                    session,
                    cine=cine,
                    pelicula_id=pelicula_id,
                    fecha_hora=fecha.replace(hour=int(match.group(1)), minute=int(match.group(2))),
                    sala=SALA,
                    idioma=IDIOMA,
                    precio=PRECIO,
                    link_compra=parsear_link(enlace.get_attribute("href")),
                    es_evento_especial=es_especial,
                )
                contadores[resultado] += 1
        except (ValueError, PlaywrightError):
            log.warning("Película descartada en %s el %s: %r", cine, fecha.date(), titulo_raw, exc_info=True)
            contadores["descartado"] += 1


def scrapear_equis():
    cine = CINES[0]
    contadores = {"creado": 0, "actualizado": 0, "descartado": 0}

    with abrir_pagina() as page, Session(engine) as session:
        _entrar_en_kinetike(page)
        lbl_fecha = page.locator("#lblContFecha")
        btn_siguiente = page.locator("#imgSiguiente")
        fecha = datetime.strptime(lbl_fecha.inner_text().strip(), "%d/%m/%Y")  # ValueError: la web ha cambiado
        if not page.locator(".panel_peli").count():
            raise FuenteNoDisponible(f"{page.url}: no hay películas")
        log.info("%s: empieza el %s, %d días", cine, fecha.date(), DIAS_A_ESCANEAR)

        for _ in range(DIAS_A_ESCANEAR):
            _leer_dia(session, page, fecha, cine, contadores)

            if not btn_siguiente.is_visible():
                break
            siguiente = fecha + timedelta(days=1)
            btn_siguiente.click()
            # Fecha y películas llegan en la misma respuesta del postback: al cambiar la etiqueta ya están las tarjetas
            try:
                expect(lbl_fecha).to_have_text(siguiente.strftime("%d/%m/%Y"), timeout=5000)
            except AssertionError:
                log.warning("%s: el calendario no pasa del %s; quedan días sin leer", cine, fecha.date())
                break
            fecha = siguiente

        session.commit()
    log.info("%s: %s", cine, contadores)


if __name__ == "__main__":
    scrapear_equis()
