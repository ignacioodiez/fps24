"""Lee: https://entradasfilmoteca.sacatuentrada.es/ (taquilla de la Filmoteca Española), todas las páginas de ul.pagination.
Extrae: un div.info por pase; título en h2.titulo ("TÍTULO (ORIGINAL,1960)"), fecha y sala en div.descripcion ("Jueves 22 de octubre a las 17:30h (Sala 1. CICLO)").
Se rompe si: cambian las clases, el texto "... de <mes> ... HH:MM (Sala N" o el enlace chevron_right; los bonos (sin fecha) se saltan."""
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
PRECIO = "3.00€"
IDIOMA = "VOSE"  # Filmoteca es VOSE por definición
MAX_PAGINAS = 10

log = obtener_logger(__name__)


def parsear_fecha(texto):
    """'... Jueves 22 de octubre a las 17:30h ...' -> datetime. ValueError si no cuadra."""
    match = re.search(r"(\d{1,2})\s+de\s+(\w+).*?(\d{2}):(\d{2})", " ".join(texto.split()), re.IGNORECASE)
    if not match:
        raise ValueError(f"Fecha no reconocida: {texto[:80]!r}")
    dia, mes_txt, h, m = match.groups()
    dia, mes = int(dia), numero_mes(mes_txt)
    return datetime(resolver_anio(mes, dia), mes, dia, int(h), int(m))


def parsear_sala(texto):
    """'... (Sala 2. CICLO)' -> 'Sala 2'; None si no aparece."""
    match = re.search(r"\(\s*sala\s*(\d+)", texto, re.IGNORECASE)
    return f"Sala {match.group(1)}" if match else None


def _leer_link(info, contadores):
    """Enlace de comprar; si aún no está a la venta, el de "+ INFO" (el frontend no tolera un href vacío)."""
    enlaces = info.locator("xpath=..").locator("div.enlaces .contenedor")
    comprar = enlaces.locator("a:not(.mas-info)")
    if comprar.count():
        link = comprar.first.get_attribute("href") or ""
    else:
        contadores["sin_comprar"] += 1
        mas_info = enlaces.locator("a.mas-info")
        link = (mas_info.first.get_attribute("href") or "") if mas_info.count() else ""
    link = link.strip()
    if link and not link.startswith("http"):
        link = f"https://entradasfilmoteca.sacatuentrada.es{link}"
    return link


def _leer_pase(session, info, cine, contadores, vistos):
    titulo_raw = None
    try:
        titulo_raw = info.locator("h2.titulo").inner_text().strip()
        descripcion = info.locator("div.descripcion").inner_text()
        if "Fecha y Hora" not in descripcion:
            log.info("Sin fecha (bono u otro producto): %r", titulo_raw)
            return
        fecha_hora = parsear_fecha(descripcion)
        if (titulo_raw, fecha_hora) in vistos:
            log.info("Pase repetido entre páginas: %r %s", titulo_raw, fecha_hora)
            return
        vistos.add((titulo_raw, fecha_hora))
        sala = parsear_sala(descripcion)
        if sala is None:
            log.info("Sin sala para %r %s", titulo_raw, fecha_hora)

        anio = re.search(r"(\d{4})\)\s*$", titulo_raw)  # "(THE APARTMENT,1960)"
        pelicula_id, es_especial = resolver_pelicula(
            session, titulo_raw, cine, anio_web=int(anio.group(1)) if anio else None)
        if pelicula_id is None:
            contadores["descartado"] += 1
            return

        resultado = registrar_pase(
            session,
            cine=cine,
            pelicula_id=pelicula_id,
            fecha_hora=fecha_hora,
            sala=sala,
            idioma=IDIOMA,
            precio=PRECIO,
            link_compra=_leer_link(info, contadores),
            es_evento_especial=es_especial,
        )
        contadores[resultado] += 1
    except (ValueError, PlaywrightError):
        log.warning("Pase descartado en %s: %r", cine, titulo_raw, exc_info=True)
        contadores["descartado"] += 1


def scrapear_dore():
    cine = CINES[0]
    contadores = {"creado": 0, "actualizado": 0, "descartado": 0, "sin_comprar": 0}
    vistos = set()  # (título, fecha_hora): un pase no se cuenta dos veces si cambia de página

    with abrir_pagina() as page, Session(engine) as session:
        page.goto(URL, wait_until="domcontentloaded")
        for n in range(1, MAX_PAGINAS + 1):
            page.wait_for_selector("div.info h2.titulo")
            bloques = page.locator("div.info").all()
            if not bloques:
                raise FuenteNoDisponible(f"{URL}: no hay pases en la página {n}")
            log.info("%s: página %d, %d productos", cine, n, len(bloques))
            for info in bloques:
                _leer_pase(session, info, cine, contadores, vistos)

            siguiente = page.locator("ul.pagination li:not(.disabled) a",
                                     has=page.locator("i", has_text="chevron_right"))
            if not siguiente.count():
                break
            if n == MAX_PAGINAS:
                log.warning("%s: tope de %d páginas alcanzado; quedan páginas sin leer", cine, MAX_PAGINAS)
                break
            page.goto(siguiente.first.get_attribute("href").strip(), wait_until="domcontentloaded")
            page.locator("ul.pagination li.active", has_text=re.compile(rf"^\s*{n + 1}\s*$")).wait_for()

        session.commit()
    log.info("%s: %s", cine, contadores)


if __name__ == "__main__":
    scrapear_dore()
