"""Self-check de GET /destacadas con datos falsos, sin red.
Uso: docker compose exec api python tests/check_destacadas.py
Vacía pase y pelicula dentro de una sesión que termina en rollback: no deja datos."""
import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import delete
from sqlmodel import Session

from app.database.engine import engine
from app.database.models import Pase, Pelicula
from app.services import destacadas as d
from app.services.cines import obtener_o_crear_cine
from main import Destacadas

if engine.url.host not in ("db", "localhost", "127.0.0.1"):
    sys.exit(f"Me niego: la BD no es local (host {engine.url.host!r})")

# Semana del 19 al 25 de octubre de 2026; el domingo 25 se pasa a horario de invierno (02:00-03:00 dos veces)
MIERCOLES = datetime(2026, 10, 21, 12, 0)
SEMANA = (date(2026, 10, 19), date(2026, 10, 25))
assert d.semana(datetime(2026, 10, 19, 0, 0)) == SEMANA         # lunes 00:00
assert d.semana(datetime(2026, 10, 25, 23, 59, 59)) == SEMANA   # domingo 23:59
assert d.semana(datetime(2026, 10, 25, 2, 30)) == SEMANA        # la hora repetida
assert d.semana(datetime(2026, 10, 26, 0, 0)) == (date(2026, 10, 26), date(2026, 11, 1))
print("OK: semana")

AUTOR, AUTOR2, COMERCIAL = 0, 1, 2

with Session(engine) as session:
    try:
        session.exec(delete(Pase))
        session.exec(delete(Pelicula))
        cines = []
        for i, tipo in enumerate(["autor", "autor", "comercial"]):
            cine = obtener_o_crear_cine(session, f"Cine de Prueba Destacadas {i}")
            cine.tipo = tipo
            session.add(cine)
            cines.append(cine.id)
        siguiente_tmdb = iter(range(9_000_000, 9_100_000))

        def peli(titulo, nota, votos, estreno=None, tmdb=True, generos="Drama"):
            p = Pelicula(titulo=titulo, nota_tmdb=nota, votos=votos, fecha_estreno=estreno, generos=generos,
                         tmdb_id=next(siguiente_tmdb) if tmdb else None)
            session.add(p)
            session.flush()
            return p

        def pase(p, fecha_hora, especial=False, cine=AUTOR, activo=True):
            session.add(Pase(pelicula_id=p.id, cine_id=cines[cine], fecha_hora=fecha_hora,
                             es_evento_especial=especial, activo=activo, sala=f"S{fecha_hora:%d%H%M}"))

        # --- estrenos ---
        a = peli("A votos 10", 7.0, 10, date(2026, 10, 23))
        pase(a, datetime(2026, 10, 20, 20))                 # antes de ahora: no cuenta
        pase(a, datetime(2026, 10, 23, 20))
        pase(a, datetime(2026, 10, 25, 23, 59), cine=COMERCIAL)  # domingo 23:59: cuenta
        pase(a, datetime(2026, 10, 26, 0, 0))               # lunes siguiente: no
        pase(a, datetime(2026, 10, 24, 20), activo=False)   # inactivo: no
        dd = peli("D", 8.0, 500, date(2026, 10, 25))
        pase(dd, datetime(2026, 10, 25, 2, 30), especial=True)  # hora repetida del cambio de hora
        b = peli("B votos 9", 9.0, 9, date(2026, 10, 19))   # relleno: 2 cines
        pase(b, datetime(2026, 10, 22, 20)); pase(b, datetime(2026, 10, 22, 21), cine=COMERCIAL)
        e = peli("E sin nota", None, None, date(2026, 10, 20))  # relleno: 3 cines, va antes que B
        for cine in (AUTOR, AUTOR2, COMERCIAL):
            pase(e, datetime(2026, 10, 22, 20), cine=cine)
        r1 = peli("R1 un cine", None, None, date(2026, 10, 20))  # 1 cine: no rellena
        pase(r1, datetime(2026, 10, 22, 20)); pase(r1, datetime(2026, 10, 23, 20))
        c = peli("C estreno el lunes siguiente", 9.0, 500, date(2026, 10, 26)); pase(c, datetime(2026, 10, 22, 20))
        peli("F sin pases", 9.0, 500, date(2026, 10, 20))

        # --- especiales (todos en cine de autor salvo que se diga) ---
        s1 = peli("S1", 9.5, 150)                             # 150 justo: entra
        pase(s1, datetime(2026, 10, 21, 20), especial=True, cine=COMERCIAL)  # cine comercial: nunca
        pase(s1, datetime(2026, 10, 22, 20), especial=True)
        pase(s1, datetime(2026, 10, 23, 20), especial=True, cine=AUTOR2)
        pase(s1, datetime(2026, 10, 22, 18))                  # no especial: nunca
        s2 = peli("S2", 9.0, 300)
        pase(s2, datetime(2026, 10, 22, 18), especial=True)   # el jueves ya lo tiene S1
        pase(s2, datetime(2026, 10, 23, 18), especial=True)   # -> viernes
        s3 = peli("S3", 8.9, 300)
        pase(s3, datetime(2026, 10, 22, 22), especial=True)   # solo jueves: jueves
        pase(peli("G votos 149", 9.9, 149), datetime(2026, 10, 22, 20), especial=True)
        pase(peli("H evento sin tmdb", 9.9, 999, tmdb=False), datetime(2026, 10, 22, 20), especial=True)
        pase(peli("K solo comercial", 9.9, 999), datetime(2026, 10, 22, 20), especial=True, cine=COMERCIAL)
        pase(peli("M concierto", 9.4, 999, generos="Documental, Música"), datetime(2026, 10, 24, 12), especial=True)
        for i in range(5):  # 9 especiales válidos en total: salen 7
            pase(peli(f"Clásico {i}", 8.0 - i / 10, 200), datetime(2026, 10, 24, 18 + i % 3), especial=True)
        session.flush()

        r = Destacadas.model_validate(d.leer_destacadas(session, MIERCOLES))
        assert (r.semana.inicio, r.semana.fin) == SEMANA
        assert [(x.pelicula.titulo, x.sin_nota) for x in r.estrenos] == [
            ("D", False), ("A votos 10", False), ("E sin nota", True), ("B votos 9", True)], r.estrenos
        ea = r.estrenos[1]
        assert (ea.pases, ea.cines, ea.primera_sesion.fecha_hora, ea.fecha_estreno, ea.votos) == (
            2, 2, datetime(2026, 10, 23, 20), date(2026, 10, 23), 10), ea
        assert r.estrenos[0].primera_sesion.fecha_hora == datetime(2026, 10, 25, 2, 30)
        assert (r.estrenos[2].cines, r.estrenos[2].votos) == (3, None)
        print("OK: estrenos (límites, umbral de votos, relleno por cines)")

        titulos = [x.pelicula.titulo for x in r.especiales]
        assert titulos == ["S1", "M concierto", "S2", "S3", "Clásico 0", "Clásico 1", "Clásico 2"], titulos
        assert len({x.pelicula.id for x in r.especiales}) == len(titulos)  # una sesión por película
        sesion = {x.pelicula.titulo: x.pase.fecha_hora for x in r.especiales}
        assert sesion["S1"] == datetime(2026, 10, 22, 20)     # la más temprana especial en cine de autor
        assert sesion["S2"] == datetime(2026, 10, 23, 18)     # el día menos repetido
        assert sesion["S3"] == datetime(2026, 10, 22, 22)
        assert r.especiales[0].nota == 9.5 and r.especiales[0].pase.cine.startswith("Cine de Prueba")
        print("OK: especiales (umbral, autor, sin estrenos ni eventos sin tmdb, Música sí, una sesión, días)")

        # Con 4 estrenos con nota no hay relleno
        for i in range(3):
            pase(peli(f"Extra {i}", 6.0 - i, 50, date(2026, 10, 19)), datetime(2026, 10, 22, 20))
        session.flush()
        r = d.leer_destacadas(session, MIERCOLES)
        assert [(x["pelicula"].titulo, x["sin_nota"]) for x in r["estrenos"]] == [
            ("D", False), ("A votos 10", False), ("Extra 0", False), ("Extra 1", False)], r["estrenos"]

        # Lunes 00:00: el pase de esa misma hora cuenta
        pase(a, datetime(2026, 10, 19, 0, 0)); session.flush()
        assert next(x for x in d.leer_destacadas(session, datetime(2026, 10, 19, 0, 0))["estrenos"]
                    if x["pelicula"].titulo == "A votos 10")["primera_sesion"].fecha_hora == datetime(2026, 10, 19)

        # Semana vacía
        r = Destacadas.model_validate(d.leer_destacadas(session, datetime(2099, 1, 7, 12)))
        assert (r.semana.inicio, r.semana.fin, r.estrenos, r.especiales) == (date(2099, 1, 5), date(2099, 1, 11), [], [])
        print("OK: sin relleno con 4 estrenos, lunes 00:00 y semana vacía")
    finally:
        session.rollback()
