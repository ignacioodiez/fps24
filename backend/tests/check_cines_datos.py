"""Self-check de la ficha de cines (CINES_DATOS, sincronizar_cines) y del análisis del geocodificador, sin red.
Uso: docker compose exec api python tests/check_cines_datos.py
Lo que toca la BD termina en rollback: no deja datos."""
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlmodel import Session, select

from app.database.engine import engine
from app.database.models import Cine, Pase, Pelicula
from app.geocodificar_cines import clave_calle, dudas, partes
from app.services.cines import CINES_CONOCIDOS, CINES_DATOS, TARIFAS, listar_cines, sincronizar_cines
from main import CineSalida

CAMPOS = {"direccion", "web", "telefono", "zona", "tipo", "lat", "lng", "tarifas"}
assert set(CINES_DATOS) <= set(CINES_CONOCIDOS.values()), set(CINES_DATOS) - set(CINES_CONOCIDOS.values())
assert all(set(d) == CAMPOS and d["tipo"] in ("autor", "comercial") for d in CINES_DATOS.values())
assert all(partes(d["direccion"])["ciudad"] == "Madrid" for d in CINES_DATOS.values())  # todas se pueden partir
assert all(40.3 < d["lat"] < 40.5 and -3.8 < d["lng"] < -3.5 for d in CINES_DATOS.values())  # en Madrid
print("OK: CINES_DATOS")

# --- tarifas: los 11 cines de frontend/src/data/cines.js, con la estructura acordada ---
DIAS = {"Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"}
assert set(TARIFAS) == {"renoir-plaza-espana", "renoir-retiro", "golem", "mk2-paz", "verdi", "pequeno-cine-estudio",
                        "embajadores", "equis", "cineteca", "dore", "mk2-palacio-hielo"}, set(TARIFAS)
assert sum(d["tarifas"] is not None for d in CINES_DATOS.values()) == 11
for slug, t in TARIFAS.items():
    assert t and set(t) <= {"entrada", "entrada_laboral", "entrada_finde", "dia_espectador", "notas"}, slug
    assert all(isinstance(t[k], float) and 0 < t[k] < 20 for k in ("entrada", "entrada_laboral", "entrada_finde") if k in t), slug
    if "dia_espectador" in t:
        de = t["dia_espectador"]
        assert set(de) == {"dias", "precio"} and de["dias"] and set(de["dias"]) <= DIAS and 0 < de["precio"] < 20, slug
assert TARIFAS["verdi"]["dia_espectador"] == {"dias": ["Lunes"], "precio": 4.9}
assert CINES_DATOS["renoir-retiro"]["direccion"].startswith("Calle de Narváez, 42")  # conflicto: manda el front
print("OK: TARIFAS")

with Session(engine) as session:
    try:
        # Uno nuevo (solo durante el test), uno con un valor que CINES_DATOS no trae y uno fuera de CINES_DATOS
        CINES_CONOCIDOS["Cine de Prueba Nuevo"] = "cine-de-prueba-nuevo"
        CINES_DATOS["cine-de-prueba-nuevo"] = dict(CINES_DATOS["dore"], zona="Nueva")
        cpp = (session.exec(select(Cine).where(Cine.slug == "cinesa-principe-pio")).first()
               or Cine(slug="cinesa-principe-pio", nombre="Cinesa Príncipe Pío"))
        cpp.web, cpp.zona = "https://ejemplo.es", "Zona vieja"  # web y tarifas: CINES_DATOS no las trae (None)
        cpp.tarifas = {"entrada": 7.5}
        otro = Cine(slug="cine-de-prueba-ficha", nombre="Cine de Prueba Ficha", zona="Sin tocar")
        session.add_all([cpp, otro])
        session.flush()

        cambiados = sincronizar_cines(session)
        assert cambiados >= 1, cambiados
        por_slug = {c.slug: c for c in session.exec(select(Cine)).all()}
        assert set(CINES_DATOS) <= set(por_slug)  # crea los que falten
        assert (por_slug["cine-de-prueba-nuevo"].nombre, por_slug["cine-de-prueba-nuevo"].zona) == ("Cine de Prueba Nuevo", "Nueva")
        cpp = por_slug["cinesa-principe-pio"]
        assert (cpp.web, cpp.zona, cpp.tarifas) == ("https://ejemplo.es", "Moncloa", {"entrada": 7.5})  # None no pisa
        assert por_slug["cinesa-principe-pio"].nombre == "Cinesa Príncipe Pío"
        assert por_slug["dore"].tarifas == TARIFAS["dore"]
        assert (por_slug["dore"].tipo, por_slug["dore"].telefono) == ("autor", "91 369 32 25")
        assert por_slug["cine-de-prueba-ficha"].zona == "Sin tocar" and por_slug["cine-de-prueba-ficha"].tipo is None
        assert sincronizar_cines(session) == 0  # idempotente
        print("OK: sincronizar_cines (crea, no pisa con None, no toca otros, idempotente, tarifas)")

        # --- listar_cines (GET /cines): pases activos de hoy desde `ahora`, sin N+1 ---
        ahora = datetime(2099, 1, 1, 12, 0)
        a, b = Pelicula(titulo="Prueba listar A"), Pelicula(titulo="Prueba listar B")
        session.add_all([a, b])
        session.flush()
        dore, verdi = por_slug["dore"], por_slug["verdi"]
        for cine, pelicula, fecha_hora, activo in [
            (dore, a, datetime(2099, 1, 1, 12, 0), True),     # justo ahora: cuenta
            (dore, a, datetime(2099, 1, 1, 23, 59), True),    # misma película: 2 sesiones, 1 película
            (dore, b, datetime(2099, 1, 1, 11, 59), True),    # antes de ahora: no
            (dore, b, datetime(2099, 1, 1, 20, 0), False),    # inactivo: no
            (dore, b, datetime(2099, 1, 2, 0, 0), True),      # mañana: no
            (verdi, a, datetime(2099, 1, 1, 18, 0), True),
            (verdi, b, datetime(2099, 1, 1, 18, 0), True),
        ]:
            session.add(Pase(cine_id=cine.id, pelicula_id=pelicula.id, fecha_hora=fecha_hora, activo=activo, sala=f"{fecha_hora}"))
        session.flush()
        consultas = []
        from sqlalchemy import event
        contar = lambda *args: consultas.append(1)
        event.listen(engine, "before_cursor_execute", contar)
        lista = [CineSalida.model_validate(c) for c in listar_cines(session, ahora)]
        event.remove(engine, "before_cursor_execute", contar)
        assert len(consultas) == 1, len(consultas)
        hoy = {c.slug: (c.sesiones_hoy, c.peliculas_hoy) for c in lista}
        assert hoy["dore"] == (2, 1) and hoy["verdi"] == (2, 2), hoy
        assert all(v == (0, 0) for k, v in hoy.items() if k not in ("dore", "verdi")), hoy
        assert len(lista) == len(por_slug)  # todos, también los que no tienen pases
        zonas = [c.zona for c in lista]
        assert zonas == sorted(zonas, key=lambda z: (z is None, z or "")), zonas  # por zona; sin zona al final
        assert next(c for c in lista if c.slug == "dore").tarifas == TARIFAS["dore"]
        print("OK: listar_cines (hoy desde ahora, activos, sin N+1, orden por zona y nombre)")
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
