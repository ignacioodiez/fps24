"""Lee: https://entradasfilmoteca.sacatuentrada.es/ (taquilla de la Filmoteca Española, solo la primera página).
Extrae: un div.info por pase; título en h2.titulo ("TÍTULO (ORIGINAL,1960)") y fecha en div.descripcion ("Jueves 22 de octubre a las 17:30h").
Se rompe si: cambian las clases o el texto "Fecha y Hora: ... de <mes> ... HH:MM"; los bonos (sin fecha) se saltan."""
import re
from datetime import datetime

from playwright.sync_api import Error as PlaywrightError
from sqlmodel import Session

from app.database.engine import engine
from app.scrapers.comun import FuenteNoDisponible, abrir_pagina, numero_mes, obtener_logger, resolver_anio
from app.services.gestor_peliculas import resolver_pelicula
from app.services.pases import registrar_pase

URL = "https://entradasfilmoteca.sacatuentrada.es/"
CINES = ["Cine Doré"]
SALA = "Sala 1"
PRECIO = "3.00€"
IDIOMA = "VOSE"  # Filmoteca es VOSE por definición

log = obtener_logger(__name__)


def parsear_fecha(texto):
    """'... Jueves 22 de octubre a las 17:30h ...' -> datetime. ValueError si no cuadra."""
    match = re.search(r"(\d{1,2})\s+de\s+(\w+).*?(\d{2}):(\d{2})", " ".join(texto.split()), re.IGNORECASE)
    if not match:
        raise ValueError(f"Fecha no reconocida: {texto[:80]!r}")
    dia, mes_txt, h, m = match.groups()
    dia, mes = int(dia), numero_mes(mes_txt)
    return datetime(resolver_anio(mes, dia), mes, dia, int(h), int(m))


def scrapear_dore():
    cine = CINES[0]
    contadores = {"creado": 0, "actualizado": 0, "descartado": 0}

    with abrir_pagina() as page, Session(engine) as session:
        page.goto(URL, wait_until="domcontentloaded")
        page.wait_for_selector("div.info h2.titulo")
        bloques = page.locator("div.info").all()
        if not bloques:
            raise FuenteNoDisponible(f"{URL}: no hay pases")
        log.info("%s: %d productos en la web", cine, len(bloques))

        for info in bloques:
            titulo_raw = None
            try:
                titulo_raw = info.locator("h2.titulo").inner_text().strip()
                descripcion = info.locator("div.descripcion").inner_text()
                if "Fecha y Hora" not in descripcion:
                    log.info("Sin fecha (bono u otro producto): %r", titulo_raw)
                    continue
                fecha_hora = parsear_fecha(descripcion)

                anio = re.search(r"(\d{4})\)\s*$", titulo_raw)  # "(THE APARTMENT,1960)"
                pelicula_id, es_especial = resolver_pelicula(
                    session, titulo_raw, cine, anio_web=int(anio.group(1)) if anio else None)
                if pelicula_id is None:
                    contadores["descartado"] += 1
                    continue

                link_elem = info.locator("xpath=..").locator(".enlaces a").first
                link_compra = link_elem.get_attribute("href") if link_elem.count() else ""
                if link_compra and not link_compra.startswith("http"):
                    link_compra = f"https://entradasfilmoteca.sacatuentrada.es{link_compra}"

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
            except (ValueError, PlaywrightError):
                log.warning("Pase descartado en %s: %r", cine, titulo_raw, exc_info=True)
                contadores["descartado"] += 1

        session.commit()
    log.info("%s: %s", cine, contadores)


if __name__ == "__main__":
    scrapear_dore()
