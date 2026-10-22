"""Camino de fallo de Cinesa: una sede con id de FilmAffinity inexistente. Comprueba que (a) la otra se guarda,
(b) al final se lanza la excepción y (c) ejecutar_scraper no desactiva ningún pase de ninguna sede.
Usa la web real y escribe en la BD: se niega a correr si la BD no es local.
Uso: docker compose exec api python tests/check_cinesa_fallo.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlmodel import Session, select

from app.database.engine import engine
from app.database.models import Cine, Pase
from app.scrapers.cines import cinesa
from app.services.pases import _ahora_utc, ejecutar_scraper

if engine.url.host not in ("db", "localhost", "127.0.0.1"):
    sys.exit(f"Me niego: la BD no es local (host {engine.url.host!r})")

ROTA = "Cinesa Proyecciones"  # la primera: así se ve que sigue con la siguiente


def activos():
    with Session(engine) as session:
        return set(session.exec(select(Pase.id).where(Pase.cine_rel.has(Cine.nombre.in_(cinesa.CINES)), Pase.activo)).all())


activos_antes = activos()
cinesa.FA_IDS = {**cinesa.FA_IDS, ROTA: "999999999"}
inicio = _ahora_utc()
try:
    ejecutar_scraper(cinesa.scrapear_cinesa)
    raise AssertionError("(b) no se lanzó la excepción")
except cinesa.FuenteNoDisponible as e:
    print("(b) OK, excepción:", e, "| causa:", type(e.__cause__).__name__, e.__cause__)

with Session(engine) as session:
    for cine in cinesa.CINES:
        vistos = len(session.exec(select(Pase.id).where(Pase.cine_rel.has(nombre=cine), Pase.visto_ultima_vez >= inicio)).all())
        print(f"   {cine}: {vistos} pases vistos")
        assert (vistos == 0) if cine == ROTA else (vistos > 0), cine
print("(a) OK: la otra sede se guarda")

perdidos = activos_antes - activos()
assert not perdidos, f"(c) desactivados: {sorted(perdidos)}"
print(f"(c) OK: 0 desactivados de {len(activos_antes)} activos previos")
