"""Lee: https://www.cinesrenoir.com/cine/<sede>/cartelera/?fecha=AAAA-MM-DD, una página por sede (Princesa, Plaza de España, Retiro) y día.
Extrae: la vista de escritorio .my-account-content.d-none.d-lg-block, una > .row por película con título en .col-4 a, versión en .col-4 small y un .col-7 .text-center por pase (span "sala 01" y a.btn-primary "HH:MM" con enlace de compra).
Se rompe si: cambian las clases, el parámetro ?fecha= o los slugs de las sedes; si falla una sede se siguen las demás y al final se lanza la excepción."""
import re
from datetime import datetime, timedelta

from playwright.sync_api import Error as PlaywrightError
from sqlmodel import Session

from app.database.engine import engine
from app.scrapers.comun import FuenteNoDisponible, abrir_pagina, hoy_madrid, obtener_logger
from app.services.gestor_peliculas import resolver_pelicula
from app.services.pases import registrar_pase

URL = "https://www.cinesrenoir.com/cine/{slug}/cartelera/"
CINES = ["Renoir Princesa", "Renoir Plaza de España", "Renoir Retiro"]
SLUGS = {
    "Renoir Princesa": "cines-princesa",
    "Renoir Plaza de España": "renoir-plaza-de-espana",
    "Renoir Retiro": "renoir-retiro",
}
PRECIO = "Consultar"
DIAS_A_ESCANEAR = 7

log = obtener_logger(__name__)


def idioma_de(textos_small):
    """['Versión Original subtitulada a Castellano', ...] -> 'VOSE'; si no, 'Español'."""
    return "VOSE" if any("subtitulada" in t.lower() for t in textos_small) else "Español"


def sala_de(texto, cine):
    """'sala 01' -> 'Renoir Retiro (Sala 01)'; sin "sala", el nombre del cine."""
    texto = (texto or "").lower()
    if "sala" not in texto:
        return cine
    return f"{cine} (Sala {texto.replace('sala', '').strip()})"


def _leer_fila(session, fila, fecha, cine, contadores):
    titulo_elem = fila.locator(".col-4 a").first
    if not titulo_elem.count():
        log.warning("%s: fila sin título el %s", cine, fecha)
        contadores["descartado"] += 1
        return
    titulo_raw = titulo_elem.inner_text().strip()
    bloques = [b for b in fila.locator(".col-7 .text-center").all() if b.locator("a.btn-primary").count()]
    if not bloques:
        return
    pelicula_id, es_especial = resolver_pelicula(session, titulo_raw, cine)
    if pelicula_id is None:
        contadores["descartado"] += 1
        return
    idioma = idioma_de(fila.locator(".col-4 small").all_inner_texts())

    for bloque in bloques:
        boton = bloque.locator("a.btn-primary").first
        hora_txt = boton.inner_text().strip()
        try:
            match = re.search(r"(\d{2}):(\d{2})", hora_txt)
            if not match:
                raise ValueError(f"Hora no reconocida: {hora_txt!r}")
            h, m = map(int, match.groups())
            span = bloque.locator("span").first
            resultado = registrar_pase(
                session,
                cine=cine,
                pelicula_id=pelicula_id,
                fecha_hora=datetime(fecha.year, fecha.month, fecha.day, h, m),
                sala=sala_de(span.inner_text() if span.count() else None, cine),
                idioma=idioma,
                precio=PRECIO,
                link_compra=boton.get_attribute("href"),
                es_evento_especial=es_especial,
            )
            contadores[resultado] += 1
        except (ValueError, PlaywrightError):
            log.warning("Pase descartado de %r en %s el %s: %r", titulo_raw, cine, fecha, hora_txt, exc_info=True)
            contadores["descartado"] += 1


def _scrapear_sede(page, session, cine, contadores):
    url = URL.format(slug=SLUGS[cine])
    hoy = hoy_madrid()
    for i in range(DIAS_A_ESCANEAR):
        fecha = hoy + timedelta(days=i)
        url_dia = f"{url}?fecha={fecha:%Y-%m-%d}"
        page.goto(url_dia, wait_until="domcontentloaded")  # si no carga, Playwright lanza la excepción
        page.wait_for_selector(".shop_list_area")
        filas = page.locator(".my-account-content.d-none.d-lg-block > .row").all()
        if not filas:
            if i == 0:
                raise FuenteNoDisponible(f"{url_dia}: no hay películas")
            log.info("%s: sin películas el %s", cine, fecha)
            continue
        for fila in filas:
            try:
                _leer_fila(session, fila, fecha, cine, contadores)
            except (ValueError, PlaywrightError):
                log.warning("Película descartada en %s el %s", cine, fecha, exc_info=True)
                contadores["descartado"] += 1


def scrapear_renoir():
    fallos = {}

    with abrir_pagina() as page, Session(engine) as session:
        for cine in CINES:
            contadores = {"creado": 0, "actualizado": 0, "descartado": 0}
            try:
                _scrapear_sede(page, session, cine, contadores)
            except (PlaywrightError, FuenteNoDisponible) as e:
                log.error("%s: la sede falla; se sigue con las demás", cine, exc_info=True)
                fallos[cine] = e
            log.info("%s: %s", cine, contadores)
        session.commit()

    # Se lanza después del commit: lo leído queda guardado y ejecutar_scraper no desactiva nada
    if fallos:
        raise FuenteNoDisponible(f"Renoir: fallan {', '.join(fallos)}") from next(iter(fallos.values()))


if __name__ == "__main__":
    scrapear_renoir()
