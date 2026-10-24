"""Self-check del registro de scrapers, --solo y el candado. No abre webs.
Uso: docker compose exec api python tests/check_run_scrapers.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import run_scrapers
from app.run_scrapers import DESHABILITADOS, REGISTRO, elegir
from app.services.cines import CINES_CONOCIDOS

CARPETA = Path(__file__).resolve().parent.parent / "app" / "scrapers" / "cines"

# Registro + deshabilitados cubren todos los módulos de scrapers, sin repetir, y sus cines son conocidos
modulos = {p.stem for p in CARPETA.glob("*.py") if not p.stem.startswith("_")}
nombres = [s.nombre for s in REGISTRO] + list(DESHABILITADOS)
assert sorted(nombres) == sorted(modulos) and len(set(nombres)) == len(nombres), (nombres, modulos)
assert all(DESHABILITADOS.values())  # cada deshabilitado con su motivo
todos = REGISTRO + (elegir(",".join(DESHABILITADOS)) if DESHABILITADOS else [])
cines = [c for s in todos for c in s.cines]
assert all(c in CINES_CONOCIDOS for c in cines), [c for c in cines if c not in CINES_CONOCIDOS]
# Cada cine una sola vez en el registro; un deshabilitado puede cubrir un cine que ya lee otra fuente
registrados = [c for s in REGISTRO for c in s.cines]
assert sorted(registrados) == sorted(CINES_CONOCIDOS), set(CINES_CONOCIDOS) ^ set(registrados)
assert all(s.funcion.__name__ == f"scrapear_{s.nombre}" for s in todos)
print("OK: registro")

# --solo: orden del registro, espacios tolerados, error claro con los válidos
assert elegir() == REGISTRO
assert [s.nombre for s in elegir("equis, dore")] == ["dore", "equis"]
for nombre in DESHABILITADOS:  # deshabilitado: solo a mano, después de los del registro
    assert [s.nombre for s in elegir(f"{nombre},dore")] == ["dore", nombre]
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
