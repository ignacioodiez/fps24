"""Self-check de GET /pases/vose. Uso: docker compose exec api python tests/check_pases_vose.py
Crea sus pases en una sesión que termina en rollback (la API usa esa misma sesión): no deja datos."""
import asyncio
import json
import sys
from datetime import datetime, time, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlmodel import Session, select

from app.database.engine import engine, get_session
from app.database.models import Pase, Pelicula
from app.services.pases import registrar_pase
from app.services.tiempo import ahora_madrid
from main import app

if engine.url.host not in ("db", "localhost", "127.0.0.1"):
    sys.exit(f"Me niego: la BD no es local (host {engine.url.host!r})")

CINE = "Cine de Prueba Check VOSE"


def llamar(ruta):
    """GET a la app por ASGI (como llamar() de check_diario.py, con las cabeceras); devuelve (status, cabeceras, cuerpo)."""
    ruta, _, query = ruta.partition("?")
    scope = {"type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1", "method": "GET", "scheme": "http",
             "path": ruta, "raw_path": ruta.encode(), "query_string": query.encode(), "root_path": "",
             "headers": [], "client": ("test", 1), "server": ("test", 80)}
    r = {"status": None, "headers": {}, "body": b""}

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(m):
        if m["type"] == "http.response.start":
            r["status"] = m["status"]
            r["headers"] = {k.decode().lower(): v.decode() for k, v in m["headers"]}
        elif m["type"] == "http.response.body":
            r["body"] += m.get("body", b"")

    asyncio.run(app(scope, receive, send))
    return r["status"], r["headers"], r["body"]


with Session(engine) as session:
    app.dependency_overrides[get_session] = lambda: session
    try:
        pelicula_id = session.exec(select(Pelicula.id)).first()
        assert pelicula_id, "hace falta al menos una película en la BD"
        manana = datetime.combine(ahora_madrid().date() + timedelta(days=1), time(20, 0))
        base = dict(cine=CINE, sala="Sala 1", pelicula_id=pelicula_id, idioma="VOSE", precio="7€",
                    link_compra="https://entradas.example/1", es_evento_especial=False)
        casos = {
            "dentro": manana,
            "lejos": manana + timedelta(days=30),  # fuera de 7 días
            "ayer": manana - timedelta(days=2),  # ya pasó
            "inactivo": manana + timedelta(hours=1),
            "doblada": manana + timedelta(hours=2),
        }
        for nombre, fecha in casos.items():
            registrar_pase(session, fecha_hora=fecha, **{**base, "idioma": "Español" if nombre == "doblada" else "VOSE"})
        session.flush()
        mios = {p.fecha_hora: p for p in session.exec(select(Pase).where(Pase.cine_rel.has(nombre=CINE))).all()}
        mios[casos["inactivo"]].activo = False
        session.flush()
        ids = {nombre: mios[fecha].id for nombre, fecha in casos.items()}

        status, cabeceras, cuerpo = llamar("/pases/vose?dias=7")
        assert status == 200, status
        assert cabeceras["cache-control"].startswith("public"), cabeceras
        datos = json.loads(cuerpo)
        devueltos = {p["id"] for p in datos["pases"]}
        assert ids["dentro"] in devueltos
        assert not devueltos & {ids["lejos"], ids["ayer"], ids["inactivo"], ids["doblada"]}, devueltos
        assert all(p["idioma"].upper().startswith("VO") for p in datos["pases"])
        assert all(p["fecha_hora"] >= ahora_madrid().isoformat(timespec="minutes")[:16] for p in datos["pases"])

        # Solo los campos públicos, y cada película una vez
        pase = next(p for p in datos["pases"] if p["id"] == ids["dentro"])
        assert set(pase) == {"id", "pelicula_id", "cine", "cine_slug", "fecha_hora", "idioma", "precio", "link_compra"}, pase
        assert (pase["cine"], pase["precio"], pase["link_compra"]) == (CINE, "7€", "https://entradas.example/1")
        assert pase["fecha_hora"] == manana.isoformat()
        assert set(datos["peliculas"][0]) == {"id", "titulo", "titulo_original", "anio", "director", "poster_url"}
        assert len({p["id"] for p in datos["peliculas"]}) == len(datos["peliculas"])
        assert {p["pelicula_id"] for p in datos["pases"]} == {p["id"] for p in datos["peliculas"]}
        assert datos["hasta"] == (ahora_madrid().date() + timedelta(days=6)).isoformat()

        # dias=1: solo hoy (mañana fuera); límites de dias
        _, _, cuerpo1 = llamar("/pases/vose?dias=1")
        assert ids["dentro"] not in {p["id"] for p in json.loads(cuerpo1)["pases"]}
        assert llamar("/pases/vose?dias=0")[0] == 422
        assert llamar("/pases/vose?dias=15")[0] == 422

        # Mucho más ligero que /pases y bajo el límite de 2 MB de la caché de Next (con el máximo de días)
        _, _, todo = llamar("/pases")
        _, _, maximo = llamar("/pases/vose?dias=14")
        assert len(cuerpo) * 5 < len(todo), (len(cuerpo), len(todo))
        assert len(maximo) < 2 * 1024 * 1024, len(maximo)
        print(f"OK: /pases/vose ({len(cuerpo) // 1024} KB a 7 días frente a {len(todo) // 1024} KB de /pases)")
    finally:
        app.dependency_overrides.pop(get_session, None)
        session.rollback()
