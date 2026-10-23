"""Self-check de GET /peliculas/buscar contra la BD local. Solo lectura (lo que inserta termina en rollback). Sin red.
Uso: docker compose exec api python tests/check_buscar_peliculas.py"""
import asyncio
import json
import sys
import unicodedata
from pathlib import Path
from urllib.parse import quote

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from sqlmodel import Session, func, select

from app.database.engine import engine
from app.database.models import Pase, Pelicula
from main import app, buscar_peliculas

if engine.url.host not in ("db", "localhost", "127.0.0.1"):
    sys.exit(f"Me niego: la BD no es local (host {engine.url.host!r})")


def llamar(metodo, ruta):
    """GET a la app por ASGI (como en check_diario.py: TestClient necesita httpx); devuelve (status, json)."""
    ruta, _, query = ruta.partition("?")
    scope = {"type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1", "method": metodo, "scheme": "http",
             "path": ruta, "raw_path": ruta.encode(), "query_string": query.encode(), "root_path": "",
             "headers": [], "client": ("test", 1), "server": ("test", 80)}
    mensajes = [{"type": "http.request", "body": b"", "more_body": False}]
    respuesta = {"status": None, "body": b""}

    async def receive():
        return mensajes.pop(0) if mensajes else {"type": "http.disconnect"}

    async def send(m):
        if m["type"] == "http.response.start":
            respuesta["status"] = m["status"]
        elif m["type"] == "http.response.body":
            respuesta["body"] += m.get("body", b"")

    asyncio.run(app(scope, receive, send))
    return respuesta["status"], json.loads(respuesta["body"]) if respuesta["body"] else None


def buscar(q, limite=20):
    codigo, cuerpo = llamar("GET", f"/peliculas/buscar?q={quote(q)}&limite={limite}")
    assert codigo == 200, (q, codigo, cuerpo)
    return cuerpo


def sin_tildes(texto):
    return "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn").lower()


with Session(engine) as session:
    con_pases = select(Pase.id).where(Pase.pelicula_id == Pelicula.id).exists()
    # Una película con tilde en el título (o la primera que haya) para buscarla de varias formas
    peli = (session.exec(select(Pelicula).where(con_pases, Pelicula.titulo.op("~")("[áéíóúñ]"))).first()
            or session.exec(select(Pelicula).where(con_pases)).first())
    assert peli, "La BD local no tiene películas con pases"
    palabras = peli.titulo.split()
    palabra = next((w for w in palabras if sin_tildes(w) != w.lower()), max(palabras, key=len))  # la de la tilde
    print(f"Película de prueba: {peli.titulo!r} (palabra {palabra!r})")

    # Coincidencia parcial (una palabra suelta y un trozo de en medio), sin distinguir mayúsculas ni tildes
    for q in {palabra, palabra.upper(), sin_tildes(palabra), sin_tildes(palabra).upper(), peli.titulo[2:6]}:
        ids = [p["id"] for p in buscar(q, 30)]
        assert peli.id in ids or len(ids) == 30, (q, ids)
    assert peli.id in [p["id"] for p in buscar(sin_tildes(peli.titulo).upper(), 30)]
    print("OK: parcial, mayúsculas y tildes")

    # Forma de cada resultado: titulo_original solo si es distinto
    r = buscar(sin_tildes(peli.titulo))[0]
    assert set(r) == {"id", "titulo", "titulo_original", "anio", "director", "poster_url", "nota_tmdb"}, r
    assert all(p["titulo_original"] != p["titulo"] for p in buscar("la", 30))
    print("OK: campos")

    # Mínimo de 2 caracteres (contando sin espacios de sobra) y límite
    assert buscar("a") == [] and buscar("") == [] and buscar("  e  ") == []
    assert len(buscar("e", 30)) == 0 and 0 < len(buscar("es", 3)) <= 3
    assert llamar("GET", "/peliculas/buscar?q=es&limite=31")[0] == 422
    assert buscar("es")[:5] == buscar("es", 5)
    print("OK: mínimo y límite")

    # Comodines de LIKE como texto literal
    assert buscar("%%") == [] or all("%" in p["titulo"] + (p["titulo_original"] or "") for p in buscar("%%"))
    assert all("_" in p["titulo"] + (p["titulo_original"] or "") for p in buscar("__"))
    print("OK: % y _ literales")

    # Orden: primero las que empiezan por la consulta (en título u original), luego las que la contienen
    for q in ("el", "la", "de", "lo"):
        res = buscar(q, 30)
        empieza = [sin_tildes(p["titulo"]).startswith(q) or sin_tildes(p["titulo_original"] or "").startswith(q) for p in res]
        assert empieza == sorted(empieza, reverse=True), (q, [p["titulo"] for p in res])
    print("OK: prefijo primero")

    # Excluidas (BONO…) y películas sin pases no salen. Se insertan y se llama a la función con esta sesión: rollback al final.
    bono = Pelicula(titulo="BONO 5 sesiones zzqx")
    sin_pases = Pelicula(titulo="Zzqx sin pases")
    session.add_all([bono, sin_pases])
    session.flush()
    session.add(Pase(pelicula_id=bono.id, cine_id=session.exec(select(Pase.cine_id)).first(), fecha_hora=peli.created_at))
    session.flush()
    assert session.exec(select(func.count()).where(Pelicula.titulo.ilike("%zzqx%"))).one() == 2
    assert buscar_peliculas(q="zzqx", limite=20, session=session) == []
    session.rollback()
    print("OK: excluidas y sin pases ausentes")

print("TODO OK: check_buscar_peliculas")
