"""Lee: https://ejemplo.com/cartelera (TODO: web real).
Extrae: una tarjeta .pelicula por película, con un enlace .pase por sesión ("17 de enero 19:30").
Se rompe si: cambian las clases .pelicula / .pase o el formato de la fecha.

PLANTILLA: no se registra ni se lanza. Cópiala a cines/<nombre>.py y cambia lo marcado con TODO.
Las reglas están en backend/SCRAPERS.md.
"""
import re
from datetime import datetime

from sqlmodel import Session

from app.database.engine import engine
from app.scrapers.comun import FuenteNoDisponible, abrir_pagina, numero_mes, obtener_logger, resolver_anio
from app.services.gestor_peliculas import resolver_pelicula
from app.services.pases import registrar_pase

URL = "https://ejemplo.com/cartelera"  # TODO
CINES = ["Cine de Ejemplo"]  # TODO: nombres canónicos de CINES_CONOCIDOS
PRECIO = "Consultar"

log = obtener_logger(__name__)

FECHA_HORA = re.compile(r"(\d{1,2}) de (\w+)\D*(\d{1,2}):(\d{2})")


def parsear_fecha_hora(texto: str) -> datetime:
    """'17 de enero 19:30' -> datetime de Madrid sin zona. ValueError si no encaja."""
    match = FECHA_HORA.search(texto)
    if not match:
        raise ValueError(f"Fecha no reconocida: {texto!r}")
    dia, mes = int(match.group(1)), numero_mes(match.group(2))
    return datetime(resolver_anio(mes, dia), mes, dia, int(match.group(3)), int(match.group(4)))


def scrapear_plantilla():  # TODO: scrapear_<nombre>
    cine = CINES[0]
    contadores = {"creado": 0, "actualizado": 0, "descartado": 0}

    with abrir_pagina() as page, Session(engine) as session:
        page.goto(URL)  # si no carga, Playwright lanza la excepción: no la captures
        tarjetas = page.locator(".pelicula").all()
        if not tarjetas:
            raise FuenteNoDisponible(f"{URL}: no hay películas")

        for tarjeta in tarjetas:
            titulo = tarjeta.locator("h2").inner_text()
            pelicula_id, es_especial = resolver_pelicula(session, titulo, cine)
            if pelicula_id is None:
                contadores["descartado"] += 1
                continue  # resolver_pelicula ya lo ha registrado

            for pase in tarjeta.locator("a.pase").all():
                try:
                    resultado = registrar_pase(
                        session,
                        cine=cine,
                        pelicula_id=pelicula_id,
                        fecha_hora=parsear_fecha_hora(pase.inner_text()),
                        sala=None,  # o un valor estable: "Sala 2", "2"
                        idioma="VOSE" if "VOSE" in titulo.upper() else "Español",
                        precio=PRECIO,
                        link_compra=pase.get_attribute("href"),
                        es_evento_especial=es_especial,
                    )
                    contadores[resultado] += 1
                except ValueError:
                    log.warning("Pase descartado de %r: %r", titulo, pase.inner_text(), exc_info=True)
                    contadores["descartado"] += 1

        session.commit()
    log.info("%s: %s", cine, contadores)
