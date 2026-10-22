"""Self-check de la ficha de cines (CINES_DATOS, sincronizar_cines) y del análisis del geocodificador, sin red.
Uso: docker compose exec api python tests/check_cines_datos.py
Lo que toca la BD termina en rollback: no deja datos."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlmodel import Session, select

from app.database.engine import engine
from app.database.models import Cine
from app.geocodificar_cines import clave_calle, dudas, partes
from app.services.cines import CINES_CONOCIDOS, CINES_DATOS, sincronizar_cines

CAMPOS = {"direccion", "web", "telefono", "zona", "tipo", "lat", "lng"}
assert set(CINES_DATOS) <= set(CINES_CONOCIDOS.values()), set(CINES_DATOS) - set(CINES_CONOCIDOS.values())
assert all(set(d) == CAMPOS and d["tipo"] in ("autor", "comercial") for d in CINES_DATOS.values())
assert all(partes(d["direccion"])["ciudad"] == "Madrid" for d in CINES_DATOS.values())  # todas se pueden partir
assert all(40.3 < d["lat"] < 40.5 and -3.8 < d["lng"] < -3.6 for d in CINES_DATOS.values())  # en Madrid
print("OK: CINES_DATOS")

with Session(engine) as session:
    try:
        # Uno nuevo (solo durante el test), uno con un valor que CINES_DATOS no trae y uno fuera de CINES_DATOS
        CINES_CONOCIDOS["Cine de Prueba Nuevo"] = "cine-de-prueba-nuevo"
        CINES_DATOS["cine-de-prueba-nuevo"] = dict(CINES_DATOS["dore"], zona="Nueva")
        mk2 = session.exec(select(Cine).where(Cine.slug == "mk2-paz")).first() or Cine(slug="mk2-paz", nombre="Cine MK2 Paz")
        mk2.web, mk2.zona = "https://ejemplo.es", "Zona vieja"  # web: CINES_DATOS no la trae (None)
        otro = Cine(slug="cine-de-prueba-ficha", nombre="Cine de Prueba Ficha", zona="Sin tocar")
        session.add_all([mk2, otro])
        session.flush()

        cambiados = sincronizar_cines(session)
        assert cambiados >= 1, cambiados
        por_slug = {c.slug: c for c in session.exec(select(Cine)).all()}
        assert set(CINES_DATOS) <= set(por_slug)  # crea los que falten
        assert (por_slug["cine-de-prueba-nuevo"].nombre, por_slug["cine-de-prueba-nuevo"].zona) == ("Cine de Prueba Nuevo", "Nueva")
        assert (por_slug["mk2-paz"].web, por_slug["mk2-paz"].zona) == ("https://ejemplo.es", "Chamberí")  # None no pisa
        assert por_slug["mk2-paz"].nombre == "Cine MK2 Paz"
        assert (por_slug["dore"].tipo, por_slug["dore"].telefono) == ("autor", "91 369 32 25")
        assert por_slug["cine-de-prueba-ficha"].zona == "Sin tocar" and por_slug["cine-de-prueba-ficha"].tipo is None
        assert sincronizar_cines(session) == 0  # idempotente
        print("OK: sincronizar_cines (crea, no pisa con None, no toca otros, idempotente)")
    finally:
        session.rollback()
        del CINES_CONOCIDOS["Cine de Prueba Nuevo"], CINES_DATOS["cine-de-prueba-nuevo"]

# --- análisis del resultado de Nominatim ---
assert partes("Centro Comercial Palacio de Hielo, Calle de Silvano, 77, 28043 Madrid") == dict(
    calle="Calle de Silvano", numero="77", cp="28043", ciudad="Madrid")
assert clave_calle("Calle de la Princesa") == clave_calle("Princesa") == "princesa"
assert clave_calle("Calle del Duque de Alba") == "duque de alba"
bueno = {"address": {"road": "Calle de Santa Isabel", "house_number": "3", "city": "Madrid", "postcode": "28012"}}
assert dudas("Calle de Santa Isabel, 3, 28012 Madrid", bueno) == []
assert dudas("Calle de Santa Isabel, 3, 28012 Madrid", None) == ["NO ENCONTRADO"]
malo = {"address": {"road": "Calle de Santa Inés", "city": "Getafe", "postcode": "28901"}}
assert [m.split(" (")[0] for m in dudas("Calle de Santa Isabel, 3, 28012 Madrid", malo)] == [
    "otra calle", "otro número", "otra ciudad", "otro CP"]
print("OK: análisis del geocodificador")
