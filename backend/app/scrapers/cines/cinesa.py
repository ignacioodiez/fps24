"""Lee: https://www.filmaffinity.com/es/theater-showtimes.php?id=<id> (cartelera de FilmAffinity), una página por sede (Proyecciones 271, Príncipe Pío 270).
Extrae: una .fa-content-card.movie por película; de su primer div.movie-showtimes-n, el título en .mv-title span.fs-5 ("Dune (VOSE)"), una div.row[data-sess-date] por día y un .sess-times a.btn por pase ("19:00", title "Sala 3 XL").
Se rompe si: cambian las clases o los ids de FilmAffinity; si falla una sede se siguen las demás y al final se lanza la excepción."""
from datetime import datetime

from playwright.sync_api import Error as PlaywrightError
from sqlmodel import Session

from app.database.engine import engine
from app.scrapers.comun import FuenteNoDisponible, abrir_pagina, obtener_logger
from app.services.gestor_peliculas import resolver_pelicula
from app.services.pases import registrar_pase

URL = "https://www.filmaffinity.com/es/theater-showtimes.php?id={}"
CINES = ["Cinesa Proyecciones", "Cinesa Príncipe Pío"]
FA_IDS = {"Cinesa Proyecciones": "271", "Cinesa Príncipe Pío": "270"}
PRECIO = "Consultar"

log = obtener_logger(__name__)


def idioma_de(titulo_sesion):
    return "VOSE" if "(VOSE)" in titulo_sesion else "Español"


def sala_de(title):
    """'Sala 3 XL' -> '3 XL'; sin title, None."""
    return (title or "").replace("Sala", "").strip() or None


def _leer_tarjeta(session, tarjeta, cine, peliculas, contadores):
    titulo_card = tarjeta.locator("div.mc-title a").first
    if not titulo_card.count():
        log.warning("%s: tarjeta sin título", cine)
        contadores["descartado"] += 1
        return
    titulo_card = titulo_card.inner_text().strip()
    # shortcut: solo el primer bloque de sesiones (otras versiones: VOSE/doblada, iSense...), como antes; leer todos con .all()
    bloque = tarjeta.locator("div.movie-showtimes-n").first
    if not bloque.count():
        log.info("%s: sin sesiones para %r", cine, titulo_card)
        return
    titulo_sesion = bloque.locator("div.mv-title span.fs-5").first
    titulo_raw = titulo_sesion.inner_text().strip() if titulo_sesion.count() else titulo_card

    if titulo_raw not in peliculas:  # Proyecciones y Príncipe Pío comparten películas: se resuelve una vez
        peliculas[titulo_raw] = resolver_pelicula(session, titulo_raw, cine)
    pelicula_id, es_especial = peliculas[titulo_raw]
    if pelicula_id is None:
        contadores["descartado"] += 1
        return

    idioma = idioma_de(titulo_raw)
    for fila in bloque.locator("div.row[data-sess-date]").all():
        fecha_str = fila.get_attribute("data-sess-date")
        for boton in fila.locator("div.sess-times a.btn").all():
            hora_txt = boton.inner_text().strip()
            try:
                fecha_hora = datetime.strptime(f"{fecha_str} {hora_txt}", "%Y-%m-%d %H:%M")
            except ValueError:
                log.warning("Pase descartado de %r en %s: %r %r", titulo_raw, cine, fecha_str, hora_txt)
                contadores["descartado"] += 1
                continue
            resultado = registrar_pase(
                session,
                cine=cine,
                pelicula_id=pelicula_id,
                fecha_hora=fecha_hora,
                sala=sala_de(boton.get_attribute("title")),
                idioma=idioma,
                precio=PRECIO,
                link_compra=boton.get_attribute("href"),
                es_evento_especial=es_especial,
            )
            contadores[resultado] += 1


def _scrapear_sede(page, session, cine, peliculas, contadores):
    url = URL.format(FA_IDS[cine])
    respuesta = page.goto(url, wait_until="domcontentloaded")
    if respuesta and respuesta.status in (403, 429):
        raise FuenteNoDisponible(f"{cine}: FilmAffinity bloqueado por Cloudflare (HTTP {respuesta.status}) en {url}")
    if respuesta and respuesta.status >= 400:
        raise FuenteNoDisponible(f"{cine}: FilmAffinity responde HTTP {respuesta.status} en {url}")
    cookies = page.get_by_role("button", name="ACEPTAR").or_(page.get_by_text("AGREE")).first
    if cookies.is_visible():
        cookies.click()
    try:
        page.wait_for_selector(".fa-content-card.movie")
    except PlaywrightError as e:
        raise FuenteNoDisponible(f"{cine}: no hay películas en {url} ({page.title()!r})") from e

    tarjetas = page.locator(".fa-content-card.movie").all()
    log.info("%s: %d películas", cine, len(tarjetas))
    for tarjeta in tarjetas:
        try:
            _leer_tarjeta(session, tarjeta, cine, peliculas, contadores)
        except PlaywrightError:
            log.warning("Película descartada en %s", cine, exc_info=True)
            contadores["descartado"] += 1


def scrapear_cinesa():
    fallos = {}
    peliculas = {}  # título de la web -> (pelicula_id, es_especial)

    with Session(engine) as session:
        for cine in CINES:
            contadores = {"creado": 0, "actualizado": 0, "descartado": 0}
            try:
                # Navegador limpio por sede: con las cookies que deja la primera (cf_clearance...), Cloudflare responde 403
                with abrir_pagina() as page:
                    _scrapear_sede(page, session, cine, peliculas, contadores)
            except (PlaywrightError, FuenteNoDisponible) as e:
                log.error("%s: la sede falla; se sigue con las demás", cine, exc_info=True)
                fallos[cine] = e
            log.info("%s: %s", cine, contadores)
        session.commit()

    # Se lanza después del commit: lo leído queda guardado y ejecutar_scraper no desactiva nada
    if fallos:
        raise FuenteNoDisponible(f"Cinesa: fallan {', '.join(fallos)}") from next(iter(fallos.values()))


if __name__ == "__main__":
    scrapear_cinesa()
