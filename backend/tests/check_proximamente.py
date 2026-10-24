"""Self-check de los próximos estrenos de /estrenos (app/proximamente, migraciones 0016 y 0017, y lo suyo en app/admin.py) contra la BD local.
Uso: docker compose exec api python tests/check_proximamente.py
Nunca llama a TMDB: tmdb._get se sustituye por respuestas simuladas y requests.get queda bloqueado. Lo que toca la BD
usa fechas de 2031 y acaba en rollback,
salvo un estreno de prueba del admin que se borra al final."""
import asyncio
import importlib.util
import json
import subprocess
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

import requests
from sqlalchemy import text
from sqlmodel import Session, delete, select

from app.database.engine import engine
from app.database.models import Cine, EstrenoProximo, Pase, Pelicula, PeliculaOculta
from app import admin
from app.auth import Usuario
from app.proximamente import actualizar, estrenos, servicio
from app.services import destacadas as d
from app.services import tmdb
from app.services.tiempo import hoy_madrid
from main import PaginaSemana, app

if engine.url.host not in ("db", "localhost", "127.0.0.1"):
    sys.exit(f"Me niego: la BD no es local (host {engine.url.host!r})")

subprocess.run(["alembic", "upgrade", "head"], cwd=BACKEND, check=True)


def _prohibido(*a, **k):
    raise AssertionError("los tests no pueden llamar a la red")


requests.get = _prohibido
servicio.PAUSA = 0

# --- fecha_espanola ---
DESDE, HASTA = date(2031, 1, 9), date(2031, 3, 6)


def fechas(*es, general=None, otros=()):
    """release_dates simulado: es = [(tipo, "AAAA-MM-DD")] de España; otros = lo mismo de EE. UU."""
    pais = lambda iso, fs: {"iso_3166_1": iso, "release_dates": [{"type": t, "release_date": f"{f}T00:00:00.000Z"} for t, f in fs]}
    return {"release_date": general, "release_dates": {"results": [pais("ES", es)] * bool(es) + [pais("US", otros)] * bool(otros)}}


assert servicio.fecha_espanola(fechas((3, "2031-01-17")), DESDE, HASTA) == (date(2031, 1, 17), True)
assert servicio.fecha_espanola(fechas((2, "2031-01-17"), (3, "2031-01-17")), DESDE, HASTA) == (date(2031, 1, 17), True)
# Dos fechas españolas distintas en la ventana: la primera, como prevista
assert servicio.fecha_espanola(fechas((2, "2031-01-10"), (3, "2031-01-24")), DESDE, HASTA) == (date(2031, 1, 10), False)
# Sin fecha española: la general, como prevista; fuera de la ventana, nada
assert servicio.fecha_espanola(fechas(general="2031-02-01", otros=[(3, "2031-01-01")]), DESDE, HASTA) == (date(2031, 2, 1), False)
assert servicio.fecha_espanola(fechas(general="2031-04-01"), DESDE, HASTA) is None
assert servicio.fecha_espanola(fechas(), DESDE, HASTA) is None
# Ya estrenada en cines en España (reestreno) o fecha española fuera de la ventana
assert servicio.fecha_espanola(fechas((3, "2030-05-01"), (3, "2031-01-17")), DESDE, HASTA) is None
assert servicio.fecha_espanola(fechas((3, "2031-05-01"), general="2031-01-20"), DESDE, HASTA) is None
# Festival (tipo 1) y digital (4) no cuentan
assert servicio.fecha_espanola(fechas((1, "2031-01-12"), (4, "2031-01-13"), (3, "2031-01-31")), DESDE, HASTA) == (date(2031, 1, 31), True)
print("OK: fecha_espanola (confirmada, prevista, reestreno, fuera de ventana)")

# --- candidatos con TMDB simulado ---
P = servicio.POPULARIDAD_MIN
DESCUBRIR = [
    dict(id=1, title="Buena", poster_path="/1.jpg", popularity=P + 10, vote_count=0),
    dict(id=2, title="Sin póster", poster_path=None, popularity=P + 10, vote_count=50),
    dict(id=3, title="Poco popular", poster_path="/3.jpg", popularity=P / 2, vote_count=servicio.VOTOS_MIN - 1),
    dict(id=4, title="De festival", poster_path="/4.jpg", popularity=P / 2, vote_count=servicio.VOTOS_MIN),
    dict(id=5, title="Gira", poster_path="/5.jpg", popularity=P + 5, vote_count=0),
    dict(id=6, title="Documental musical", poster_path="/6.jpg", popularity=P + 5, vote_count=0),
    dict(id=7, title="Reestreno", poster_path="/7.jpg", popularity=P + 5, vote_count=0),
    dict(id=8, title="Adulta", poster_path="/8.jpg", popularity=P + 5, vote_count=0, adult=True),
]
DETALLES = {
    1: dict(fechas((3, "2031-01-17")), title="Buena", original_title="Good", poster_path="/1.jpg", overview="Sinopsis.",
            genres=[{"name": "Drama"}, {"name": "Comedia"}], popularity=P + 10, vote_count=0, original_language="en"),
    4: dict(fechas(general="2031-02-07"), title="De festival", original_title="De festival", poster_path="/4.jpg",
            overview="", genres=[], popularity=P / 2, vote_count=servicio.VOTOS_MIN, original_language="es"),
    5: dict(fechas((3, "2031-01-17")), title="SEVENTEEN WORLD TOUR", poster_path="/5.jpg", genres=[{"name": "Música"}]),
    6: dict(fechas((3, "2031-01-17")), title="Un concierto", poster_path="/6.jpg", genres=[{"name": "Documental"}, {"name": "Música"}]),
    7: dict(fechas((3, "1999-01-01"), (3, "2031-01-17")), title="Reestreno", poster_path="/7.jpg", genres=[]),
}
peticiones = []


def tmdb_falso(ruta, **p):
    peticiones.append((ruta, p))
    if ruta == "/discover/movie":
        assert (p["region"], p["with_release_type"], p["release_date.gte"], p["release_date.lte"]) == (
            "ES", "2|3", DESDE.isoformat(), HASTA.isoformat()), p
        # La página 2 repite la 1: sin duplicados
        return {"results": DESCUBRIR if p["page"] == 1 else DESCUBRIR[:1], "total_pages": 2}
    assert p == {"language": "es-ES", "append_to_response": "release_dates"}, p
    return DETALLES[int(ruta.rsplit("/", 1)[1])]


tmdb._get = tmdb_falso
filas = servicio.candidatos(DESDE, HASTA)
assert [f["tmdb_id"] for f in filas] == [1, 4], filas
assert filas[0] == dict(tmdb_id=1, titulo="Buena", titulo_original="Good", fecha_es=date(2031, 1, 17), fecha_confirmada=True,
                        poster_path="/1.jpg", sinopsis="Sinopsis.", popularidad=P + 10, votos=0, generos="Drama, Comedia",
                        idioma_original="en"), filas[0]
assert (filas[1]["fecha_es"], filas[1]["fecha_confirmada"], filas[1]["sinopsis"], filas[1]["generos"]) == (date(2031, 2, 7), False, None, None)
detalles_pedidos = sorted(r for r, _ in peticiones if r != "/discover/movie")
assert detalles_pedidos == ["/movie/1", "/movie/4", "/movie/5", "/movie/6", "/movie/7"], detalles_pedidos  # sin 2, 3, 8 ni repetidas
assert sum(r == "/discover/movie" for r, _ in peticiones) == 2  # se para en total_pages
print("OK: candidatos (umbrales, sin póster, adultas, eventos, reestrenos, duplicados; detalles solo de las que pasan)")


# --- main: si TMDB falla o no devuelve nada, no toca la tabla ---
def falla(*a, **k):
    raise tmdb.TmdbNoDisponible("simulado")


with Session(engine) as session:
    antes = session.exec(select(EstrenoProximo.tmdb_id, EstrenoProximo.actualizado_en)).all()
for simulado in (falla, lambda *a: []):
    servicio.candidatos, real = simulado, servicio.candidatos
    try:
        actualizar.main(hoy=DESDE - timedelta(days=1))
        raise AssertionError("debería salir con error")
    except SystemExit as e:
        assert e.code and "no se toca estreno_proximo" in str(e.code), e.code
    finally:
        servicio.candidatos = real
with Session(engine) as session:
    assert session.exec(select(EstrenoProximo.tmdb_id, EstrenoProximo.actualizado_en)).all() == antes
print("OK: TMDB caído o vacío -> exit 1 sin tocar la tabla")

# --- refrescar (caducidad, fuera de la ventana, oculta) y /estrenos (fusión, sin_sesiones, ocultas) ---
HOY = date(2031, 1, 8)      # miércoles; semana del lunes 6 al domingo 12
AHORA = datetime(2031, 1, 8, 12, 0)
ID = 990_200_000


def fila(n, fecha, **k):
    return dict(dict(tmdb_id=ID + n, titulo=f"Chk prox {n}", titulo_original=f"Chk prox {n}", fecha_es=fecha,
                     fecha_confirmada=True, poster_path=f"/{n}.jpg", sinopsis=None, popularidad=float(n), votos=0,
                     generos=None, idioma_original="en"), **k)


def mias(pagina):
    """(tmdb_id - ID, sin_sesiones) de las películas de prueba de una página de /estrenos, en orden."""
    return [(x.pelicula.tmdb_id - ID, x.sin_sesiones) for x in pagina.peliculas
            if x.pelicula.tmdb_id and ID < x.pelicula.tmdb_id < ID + 100]


with Session(engine) as session:
    try:
        session.add_all([EstrenoProximo(**fila(1, HOY - timedelta(days=8))),    # caduca: hace más de 7 días
                         EstrenoProximo(**fila(2, HOY - timedelta(days=2))),    # se queda: estrenada el lunes
                         EstrenoProximo(**fila(3, HOY + timedelta(days=20))),   # ya no la devuelve TMDB: fuera
                         EstrenoProximo(**fila(4, HOY + timedelta(days=9), titulo="Viejo")),
                         EstrenoProximo(**fila(9, HOY + timedelta(days=4), oculta=True)),     # oculta y TMDB la sigue dando
                         EstrenoProximo(**fila(10, HOY + timedelta(days=25), oculta=True))])  # oculta y TMDB ya no la da
        session.flush()
        nuevas = [fila(4, HOY + timedelta(days=10), fecha_confirmada=False), fila(5, HOY + timedelta(days=2)),
                  fila(6, HOY + timedelta(days=2), titulo_original="Original"), fila(7, HOY + timedelta(days=4)),
                  fila(8, HOY + timedelta(days=30)), fila(9, HOY + timedelta(days=5))]
        resumen = actualizar.refrescar(session, nuevas, HOY)
        # caducadas también cuenta las filas reales de la BD local (todas anteriores a 2031); el rollback las devuelve
        assert (resumen["guardadas"], resumen["fuera"]) == (6, 1) and resumen["caducadas"] >= 1, resumen
        session.expire_all()
        guardadas = {e.tmdb_id - ID: e for e in session.exec(select(EstrenoProximo).where(EstrenoProximo.tmdb_id.between(ID, ID + 99)))}
        assert sorted(guardadas) == [2, 4, 5, 6, 7, 8, 9, 10], sorted(guardadas)
        assert (guardadas[4].titulo, guardadas[4].fecha_es, guardadas[4].fecha_confirmada) == ("Chk prox 4", HOY + timedelta(days=10), False)
        assert guardadas[9].oculta and guardadas[9].fecha_es == HOY + timedelta(days=5) and guardadas[10].oculta
        assert not guardadas[5].oculta
        print("OK: refrescar (upsert sin pisar oculta, caducidad a los 7 días, quita lo que TMDB ya no da salvo ocultas)")

        # 5: con sesiones esta semana -> una sola vez, como película con sesiones; 6: ficha sin sesiones futuras ->
        # sin_sesiones; 7: ficha oculta (pelicula_oculta); 9: estreno_proximo.oculta
        cine = Cine(slug="chk-proximamente", nombre="Cine Chk Próximamente")
        p5, p6, p7 = (Pelicula(titulo=f"Chk prox {n}", tmdb_id=ID + n, fecha_estreno=HOY + timedelta(days=2)) for n in (5, 6, 7))
        session.add_all([cine, p5, p6, p7])
        session.flush()
        session.add_all([Pase(pelicula_id=p5.id, cine_id=cine.id, fecha_hora=AHORA + timedelta(days=3)),
                         Pase(pelicula_id=p6.id, cine_id=cine.id, fecha_hora=AHORA - timedelta(hours=1)),
                         Pase(pelicula_id=p6.id, cine_id=cine.id, fecha_hora=AHORA + timedelta(days=3), activo=False),
                         PeliculaOculta(pelicula_id=p7.id)])
        session.flush()

        semanas = [PaginaSemana.model_validate(estrenos.leer_estrenos(session, n, AHORA)) for n in range(d.SEMANAS_MAX_ESTRENOS + 1)]
        assert [(s.semana, s.hay_anterior, s.hay_siguiente) for s in semanas] == [(n, n > 0, n < 8) for n in range(9)]
        assert semanas[0].desde == date(2031, 1, 6) and semanas[8].hasta == date(2031, 3, 9)
        assert mias(semanas[0]) == [(5, False), (2, True), (6, True)], mias(semanas[0])  # con sesiones primero; fecha, popularidad
        assert mias(semanas[1]) == [(4, True)] and mias(semanas[2]) == [] and mias(semanas[4]) == [(8, True)]  # 7/2
        todas = [m for s in semanas for m, _ in mias(s)]
        assert len(todas) == len(set(todas)) and 7 not in todas and 9 not in todas and 10 not in todas
        x2 = next(x for x in semanas[0].peliculas if x.pelicula.tmdb_id == ID + 2)
        assert (x2.pelicula.id, x2.sesion, x2.alternativas, x2.n_sesiones, x2.n_cines, x2.sin_nota) == (None, None, [], 0, 0, True)
        assert (x2.pelicula.fecha_estreno, x2.pelicula.fecha_confirmada) == (HOY - timedelta(days=2), True)
        assert x2.pelicula.poster_url == "https://image.tmdb.org/t/p/w500/2.jpg"
        assert next(x for x in semanas[1].peliculas if x.pelicula.tmdb_id == ID + 4).pelicula.fecha_confirmada is False
        x5 = next(x for x in semanas[0].peliculas if x.pelicula.tmdb_id == ID + 5)
        assert x5.pelicula.id == p5.id and x5.sesion and x5.n_sesiones == 1 and not x5.sin_sesiones
        assert next(x for x in semanas[0].peliculas if x.pelicula.tmdb_id == ID + 6).pelicula.titulo_original == "Original"
        assert x2.pelicula.titulo_original is None  # igual que el título
        print("OK: /estrenos 0..8 (con sesiones primero, sin duplicados, sin_sesiones sin cines ni horarios, ocultas fuera)")
    finally:
        session.rollback()


# --- HTTP por ASGI (TestClient necesita httpx, que no está instalado): límites y admin ---
def llamar(metodo, ruta):
    ruta, _, query = ruta.partition("?")
    scope = {"type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1", "method": metodo, "scheme": "http",
             "path": ruta, "raw_path": ruta.encode(), "query_string": query.encode(), "root_path": "",
             "headers": [], "client": ("test", 1), "server": ("test", 80)}
    respuesta = {"status": None, "body": b""}

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(m):
        if m["type"] == "http.response.start":
            respuesta["status"] = m["status"]
        elif m["type"] == "http.response.body":
            respuesta["body"] += m.get("body", b"")

    asyncio.run(app(scope, receive, send))
    return respuesta["status"], json.loads(respuesta["body"]) if respuesta["body"] else None


for mala in ("-1", "9", "x"):
    assert llamar("GET", f"/estrenos?semana={mala}")[0] == 422, mala
for n in range(9):
    status, cuerpo = llamar("GET", f"/estrenos?semana={n}")
    assert status == 200 and cuerpo["semana"] == n and cuerpo["hay_siguiente"] == (n < 8), (n, status)
assert llamar("GET", "/especiales?semana=4")[0] == 422  # /especiales sigue en 0..3
assert llamar("GET", "/proximamente")[0] == 404  # el endpoint ya no existe
print("OK: HTTP /estrenos?semana=0..8, 9 rechazado; /especiales sin cambios")

# Admin: un estreno sin ficha en la BD de verdad (a 3 semanas), que se borra al final
app.dependency_overrides[admin.admin_actual] = lambda: Usuario(id="chk-prox", email="admin@ejemplo.es")
lunes = d.semana(datetime.combine(hoy_madrid(), datetime.min.time()))[0]
tid = ID + 50
try:
    with Session(engine) as session:
        session.add(EstrenoProximo(**fila(50, lunes + timedelta(weeks=3, days=4), titulo="Chkproxadmin estreno")))
        session.commit()
    en_estrenos = lambda: tid in {x["pelicula"]["tmdb_id"] for x in llamar("GET", "/estrenos?semana=3")[1]["peliculas"]}
    assert en_estrenos()
    status, buscadas = llamar("GET", "/admin/peliculas/buscar?q=chkproxadmin")
    assert status == 200 and [(b["tmdb_id"], b["id"], b["sin_ficha"], b["oculta"]) for b in buscadas] == [(tid, None, True, False)], buscadas
    assert llamar("POST", f"/admin/estrenos-proximos/{tid}/ocultar")[0] == 204
    assert llamar("POST", f"/admin/estrenos-proximos/{tid}/ocultar")[0] == 204  # idempotente
    assert not en_estrenos() and llamar("GET", "/admin/peliculas/buscar?q=chkproxadmin")[1][0]["oculta"]
    assert any(o["tmdb_id"] == tid and o["sin_ficha"] and o["id"] is None for o in llamar("GET", "/admin/peliculas/ocultas")[1])
    assert llamar("DELETE", f"/admin/estrenos-proximos/{tid}/ocultar")[0] == 204
    assert en_estrenos() and not any(o["tmdb_id"] == tid for o in llamar("GET", "/admin/peliculas/ocultas")[1])
    assert llamar("POST", f"/admin/estrenos-proximos/{ID + 99}/ocultar")[0] == 404
    print("OK: admin busca, oculta y muestra estrenos sin ficha (y /estrenos lo respeta)")
finally:
    app.dependency_overrides.clear()
    with Session(engine) as session:
        session.exec(delete(EstrenoProximo).where(EstrenoProximo.tmdb_id == tid))
        session.commit()

# --- RLS de estreno_proximo (como en check_rls, en una transacción con rollback) ---
spec = importlib.util.spec_from_file_location("m0016", BACKEND / "migrations/versions/0016_estreno_proximo.py")
m0016 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m0016)
with engine.connect() as conn:
    try:
        assert conn.execute(text("SELECT relrowsecurity FROM pg_class WHERE oid = 'public.estreno_proximo'::regclass")).scalar()
        for rol in ("anon", "authenticated"):
            if not conn.execute(text("SELECT 1 FROM pg_roles WHERE rolname = :r"), {"r": rol}).scalar():
                conn.execute(text(f"CREATE ROLE {rol} NOLOGIN"))
        conn.execute(text("GRANT ALL ON public.estreno_proximo TO anon, authenticated"))
        conn.execute(text(m0016.SQL_RLS))
        for rol in ("anon", "authenticated"):
            assert not conn.execute(text("SELECT has_table_privilege(:r, 'public.estreno_proximo', 'SELECT')"), {"r": rol}).scalar(), rol
    finally:
        conn.rollback()
print("OK: RLS y REVOKE a anon/authenticated en estreno_proximo")
print("OK: check_proximamente")
