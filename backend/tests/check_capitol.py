"""Self-check del scraper de Capitol con muestras de HTML guardadas (03/11/2026). No toca la red.
Uso: docker compose exec api python tests/check_capitol.py
La parte de idempotencia escribe en la BD local de verdad (dos ejecuciones con commit): borra lo que crea."""
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import delete
from sqlmodel import Session, select

from app.database.engine import engine
from app.database.models import Cine, Pase, Pelicula
from app.scrapers.cines import capitol
from app.services.cines import CINES_CONOCIDOS, CINES_DATOS

MUESTRAS = Path(__file__).resolve().parent / "muestras"
CARTELERA = (MUESTRAS / "capitol_cine.html").read_text(encoding="utf-8")
FICHAS = {capitol.BASE + f"/es/cartelera/{s}/": (MUESTRAS / f"capitol_{s.replace('-', '_')}.html").read_text(encoding="utf-8")
          for s in ("wildwood", "la-bola-negra")}  # en el orden de la cartelera

# --- cartelera: las fichas, sin repetir y sin el ancla #comprar-entradas ---
assert capitol.leer_cartelera(CARTELERA) == list(FICHAS), capitol.leer_cartelera(CARTELERA)
print("OK: cartelera")

# --- ficha: título, días de las pestañas, hora, versión y enlace directo a admit-one ---
bola = capitol.leer_ficha(FICHAS[capitol.BASE + "/es/cartelera/la-bola-negra/"])
assert [(s.fecha_hora, s.link) for s in bola[:2]] == [
    (datetime(2026, 11, 3, 15, 45), "https://capitol.admit-one.eu/?p=tickets&perfCode=38723"),
    (datetime(2026, 11, 3, 18, 30), "https://capitol.admit-one.eu/?p=tickets&perfCode=38727")], bola[:2]
assert len(bola) == 6 and {s.titulo for s in bola} == {"LA BOLA NEGRA"} and {s.idioma for s in bola} == {"Español"}
assert Counter(s.fecha_hora.date().day for s in bola) == {3: 3, 4: 3}
wild = capitol.leer_ficha(FICHAS[capitol.BASE + "/es/cartelera/wildwood/"])
assert len(wild) == 6 and {s.titulo for s in wild} == {"WILDWOOD"} and {s.idioma for s in wild} == {"Español"}  # doblada
assert len({s.link for s in bola + wild}) == 12  # un enlace por sesión
vose = FICHAS[capitol.BASE + "/es/cartelera/wildwood/"].replace("<span>ESPAÑOL</span>", "<span>INGLÉS</span>")
assert {s.idioma for s in capitol.leer_ficha(vose)} == {"VOSE"}
assert capitol.idioma_de("ESPAÑOL", " (2D) VOSE") == "VOSE" and capitol.idioma_de("V.O.S.E.") == "VOSE"
assert capitol.idioma_de("") == capitol.idioma_de("CASTELLANO") == "Español"
sin_compra = FICHAS[capitol.BASE + "/es/cartelera/wildwood/"].replace('id="comprar-entradas"', 'id="otra-cosa"')
assert capitol.leer_ficha(sin_compra) == []  # anunciada, sin sesiones
try:
    capitol.leer_ficha("<html></html>")
    raise AssertionError("ficha sin título aceptada")
except ValueError:
    pass
print("OK: ficha")

# --- leer_cine: PAUSA antes de cada ficha y tope de peticiones ---
pedidas, pausas = [], []
obtener = lambda url: pedidas.append(url) or (CARTELERA if url == capitol.URL else FICHAS[url])
c = {"descartado": 0}
assert len(capitol.leer_cine(c, obtener=obtener, dormir=pausas.append)) == 12
assert pedidas == [capitol.URL, *FICHAS] and pausas == [capitol.PAUSA] * 2 and c["peticiones"] == 3
assert capitol.PAUSA >= 60  # Crawl-delay de su robots.txt
muchas = "".join(f'<a href="/es/cartelera/p{i}/">' for i in range(capitol.MAX_PETICIONES))
try:
    capitol.leer_cine({}, obtener=lambda url: muchas, dormir=lambda s: None)
    raise AssertionError("tope de peticiones no aplicado")
except capitol.FuenteNoDisponible:
    pass
print("OK: leer_cine")

# --- alta del cine ---
slug = CINES_CONOCIDOS[capitol.CINES[0]]
assert slug == "capitol" and CINES_DATOS[slug]["tarifas"] is None and CINES_DATOS[slug]["web"] == capitol.URL
print("OK: alta")

# --- idempotencia en la BD local: dos ejecuciones, la segunda no crea nada ---
if engine.url.host not in ("db", "localhost", "127.0.0.1"):
    sys.exit(f"Me niego: la BD no es local (host {engine.url.host!r})")

with Session(engine) as session:
    habia_cine = session.exec(select(Cine.id).where(Cine.slug == slug)).first() is not None
    peliculas = {t: Pelicula(titulo=f"Prueba check_capitol {t}") for t in ("WILDWOOD", "LA BOLA NEGRA")}
    session.add_all(peliculas.values())
    session.commit()
    ids = {t: p.id for t, p in peliculas.items()}

leer_original, resolver_original = capitol.leer_cine, capitol.resolver_pelicula
capitol.leer_cine = lambda contadores: leer_original(contadores, obtener=obtener, dormir=lambda s: None)
capitol.resolver_pelicula = lambda session, titulo, cine: (ids[titulo], False)
try:
    primera, segunda = capitol.scrapear_capitol(), capitol.scrapear_capitol()
    assert (primera["creado"], primera["actualizado"]) == (12, 0), primera
    assert (segunda["creado"], segunda["actualizado"]) == (0, 12), segunda
    with Session(engine) as session:
        pases = session.exec(select(Pase).where(Pase.pelicula_id.in_(ids.values()))).all()
        assert len(pases) == 12 and {p.sala for p in pases} == {capitol.SALA}, len(pases)
        assert all(p.link_compra.startswith("https://capitol.admit-one.eu/") and p.cine_id for p in pases)
    print("OK: idempotente (12 pases, la segunda vez 0 creados)")
finally:
    capitol.leer_cine, capitol.resolver_pelicula = leer_original, resolver_original
    with Session(engine) as session:
        session.exec(delete(Pase).where(Pase.pelicula_id.in_(ids.values())))
        session.exec(delete(Pelicula).where(Pelicula.id.in_(ids.values())))
        if not habia_cine:
            session.exec(delete(Cine).where(Cine.slug == slug))
        session.commit()
