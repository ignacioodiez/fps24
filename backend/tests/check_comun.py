"""Self-check de services/tiempo, scrapers/comun y resolver_pelicula.
Uso: docker compose exec api python tests/check_comun.py
Lo que toca la BD termina en rollback: no deja datos."""
import logging
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlmodel import Session, select

from app.database.engine import engine
from app.database.models import Pelicula
from app.scrapers.comun import MESES, abrir_pagina, numero_mes, obtener_logger
from app.services.gestor_peliculas import ANTIGUEDAD_CLASICO, analizar_titulo, es_especial, resolver_pelicula
from app.services.tiempo import ahora_madrid, hoy_madrid, resolver_anio

# --- tiempo ---
ahora = ahora_madrid()
assert ahora.tzinfo is None
assert hoy_madrid() == ahora.date()

assert resolver_anio(1, 10, hoy=date(2026, 11, 20)) == 2027        # noviembre -> enero
assert resolver_anio(1, 10, hoy=date(2026, 12, 28)) == 2027        # diciembre -> enero
assert resolver_anio(12, 31, hoy=date(2027, 1, 2)) == 2026         # ayer, cambio de año
assert resolver_anio(10, 1, hoy=date(2026, 10, 22)) == 2026        # hace 21 días
assert resolver_anio(9, 1, hoy=date(2026, 10, 22)) == 2027         # hace >30 días -> año siguiente
assert resolver_anio(3, 15, hoy=date(2026, 3, 15)) == 2026         # hoy mismo
assert resolver_anio(2, 29, hoy=date(2027, 12, 1)) == 2028         # solo 2028 tiene 29 de febrero
try:
    resolver_anio(2, 29, hoy=date(2026, 5, 1))                     # 2028 queda fuera de la ventana
    raise AssertionError("29/02 sin año válido debería lanzar ValueError")
except ValueError:
    pass
print("OK: tiempo")

# --- comun ---
assert numero_mes("Enero") == 1 and numero_mes("ENE.") == 1 and numero_mes(" sept. ") == 9
assert numero_mes("Septiembre") == 9 and numero_mes("dic") == 12
assert all(k == k.lower() and k.isascii() for k in MESES)
try:
    numero_mes("brumario")
    raise AssertionError("mes desconocido debería lanzar ValueError")
except ValueError:
    pass

log = obtener_logger("__main__")
raiz = logging.getLogger("app.scrapers")
assert log.name == "app.scrapers.__main__" and obtener_logger("app.scrapers.cines.x").name == "app.scrapers.cines.x"
assert raiz.propagate is False and len(raiz.handlers) == 1 and raiz.handlers[0].stream is sys.stdout
obtener_logger("otro")
assert len(raiz.handlers) == 1  # no duplica el handler

with abrir_pagina(timeout_ms=1234) as page:
    page.set_content("<p>hola</p>")
    assert page.locator("p").inner_text() == "hola"
    assert page.evaluate("navigator.language") == "es-ES"
    assert page.evaluate("Intl.DateTimeFormat().resolvedOptions().timeZone") == "Europe/Madrid"
print("OK: comun")

# --- regla de especial ---
anio = hoy_madrid().year
assert es_especial("Ciclo Bergman: Persona") is True                # PROGRAMACION
# Año reciente: que solo decida el título
for titulo in ["Met Opera: La Traviata", "Ballet: Giselle", "Concierto: X", "Gala de ballet: Giselle",
               "Royal Ballet - El cascanueces", "Recital de piano", "El lago de los cisnes (en diferido)"]:
    assert es_especial(titulo, anio) is True, titulo
for titulo in ["El fantasma de la ópera", "El concierto", "Operación Valkiria",
               "Misión imposible: Operación", "Documental sobre el festival"]:
    assert es_especial(titulo, anio) is False, titulo
assert es_especial("Una película", anio - ANTIGUEDAD_CLASICO - 1) is True   # hoy: 2022
assert es_especial("Una película", anio - ANTIGUEDAD_CLASICO) is False      # hoy: 2023
assert es_especial("Una película", None) is False

# PALABRAS_ESPECIAL no limpia el título: "ópera" sigue ahí
assert analizar_titulo("El fantasma de la ópera").limpio == "El fantasma de la ópera"
assert analizar_titulo("El fantasma de la ópera (VOSE)").limpio == "El fantasma de la ópera"
print("OK: regla de especial")

# --- resolver_pelicula (con una película de TMDB que ya existe: no llama a TMDB) ---
with Session(engine) as session:
    try:
        peli = Pelicula(titulo="Película de Prueba Check", tmdb_id=990_000_999, anio=hoy_madrid().year)
        session.add(peli)
        session.flush()
        pelicula_id, especial = resolver_pelicula(session, peli.titulo, "Cine de Prueba")
        assert pelicula_id == peli.id
        assert especial == es_especial(peli.titulo, peli.anio)
        # El año de la web manda sobre el de la BD/TMDB
        assert resolver_pelicula(session, peli.titulo, "Cine de Prueba", anio_web=1950) == (peli.id, True)
    finally:
        session.rollback()
print("OK: resolver_pelicula")
