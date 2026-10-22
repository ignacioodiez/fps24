"""Self-check del registro de scrapers, --solo y el candado. No abre webs.
Uso: docker compose exec api python tests/check_run_scrapers.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import run_scrapers
from app.run_scrapers import REGISTRO, elegir
from app.services.cines import CINES_CONOCIDOS

CARPETA = Path(__file__).resolve().parent.parent / "app" / "scrapers" / "cines"

# El registro cubre todos los módulos de scrapers, sin repetir, y sus cines son conocidos
modulos = {p.stem for p in CARPETA.glob("*.py") if not p.stem.startswith("_")}
nombres = [s.nombre for s in REGISTRO]
assert sorted(nombres) == sorted(modulos) and len(set(nombres)) == len(nombres), (nombres, modulos)
cines = [c for s in REGISTRO for c in s.cines]
assert all(c in CINES_CONOCIDOS for c in cines), [c for c in cines if c not in CINES_CONOCIDOS]
assert sorted(cines) == sorted(CINES_CONOCIDOS), set(CINES_CONOCIDOS) ^ set(cines)  # y cada cine una sola vez
assert all(s.funcion.__name__ == f"scrapear_{s.nombre}" for s in REGISTRO)
print("OK: registro")

# --solo: orden del registro, espacios tolerados, error claro con los válidos
assert elegir() == REGISTRO
assert [s.nombre for s in elegir("equis, dore")] == ["dore", "equis"]
for malo in ["dore,palacio_prensa", "", " , "]:
    try:
        elegir(malo)
        raise AssertionError(f"{malo!r} no ha fallado")
    except ValueError as e:
        assert "Válidos: dore," in str(e), e
try:
    run_scrapers.main(["--solo", "noexiste"])
    raise AssertionError("--solo noexiste no ha fallado")
except SystemExit as e:
    assert e.code == 2, e.code
print("OK: --solo")

# Candado: con Postgres, la segunda ejecución a la vez no lo obtiene; al salir se libera
if run_scrapers.engine.dialect.name == "postgresql":
    with run_scrapers._Candado() as primero:
        with run_scrapers._Candado() as segundo:
            assert primero and not segundo
        assert run_scrapers.lanzar_todo("dore") is None   # sale sin hacer nada
    with run_scrapers._Candado() as otra_vez:
        assert otra_vez
    print("OK: candado")
