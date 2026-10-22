"""Utilidades comunes de los scrapers del contrato (ver backend/SCRAPERS.md)."""
import logging
import sys
from contextlib import contextmanager

from playwright.sync_api import sync_playwright

from app.services.cines import normalizar
from app.services.tiempo import ahora_madrid, hoy_madrid, resolver_anio  # noqa: F401 (se reexportan)

# Claves sin tildes y en minúsculas: búscalas con numero_mes(), no directamente.
MESES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6, "julio": 7,
    "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
    "ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6, "jul": 7,
    "ago": 8, "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dic": 12,
}


def numero_mes(texto: str) -> int:
    """'Enero', 'ene.', 'SEPT' -> número de mes. ValueError si no lo reconoce."""
    clave = normalizar(texto).strip(" .")
    if clave not in MESES:
        raise ValueError(f"Mes no reconocido: {texto!r}")
    return MESES[clave]


class FuenteNoDisponible(Exception):
    """La web no carga o no devuelve nada que leer. El scraper la lanza en vez de hacer return."""


_RAIZ = "app.scrapers"


def obtener_logger(nombre: str) -> logging.Logger:
    """Logger de scraper: escribe en stdout con formato común. Uso: log = obtener_logger(__name__)."""
    raiz = logging.getLogger(_RAIZ)
    if not raiz.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s"))
        raiz.addHandler(handler)
        raiz.setLevel(logging.INFO)
        raiz.propagate = False
    # Al ejecutar un archivo suelto __name__ es "__main__": se cuelga igualmente de la raíz.
    if not nombre.startswith(_RAIZ):
        nombre = f"{_RAIZ}.{nombre}"
    return logging.getLogger(nombre)


USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36")


@contextmanager
def abrir_pagina(timeout_ms=15_000, navegacion_ms=60_000, **opciones_contexto):
    """Abre Chromium headless y entrega una página; cierra el navegador siempre.
    timeout_ms vale para esperas y clics, navegacion_ms para goto. opciones_contexto
    pisa los valores por defecto de browser.new_context (user_agent, viewport...)."""
    opciones = dict(user_agent=USER_AGENT, viewport={"width": 1920, "height": 1080},
                    locale="es-ES", timezone_id="Europe/Madrid") | opciones_contexto
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
        try:
            page = browser.new_context(**opciones).new_page()
            page.set_default_timeout(timeout_ms)
            page.set_default_navigation_timeout(navegacion_ms)
            yield page
        finally:
            browser.close()
