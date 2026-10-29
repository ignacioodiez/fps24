"""Self-check del diario (migración 0010 y endpoints de app/diario.py) contra la BD local. Sin red.
Uso: docker compose exec api python tests/check_diario.py
Llama a la app por ASGI con un cliente mínimo de stdlib (TestClient necesita httpx, que no está instalado),
con usuario_actual sustituido por dos usuarios de prueba. Borra al final todas las entradas que crea."""
import asyncio
import importlib.util
import json
import subprocess
import sys
import uuid
from datetime import datetime, time, timedelta
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, delete, select

from app import auth
from app.auth import Usuario, usuario_actual
from app.database.engine import engine
from app.database.models import DiarioEntrada, Pase, Pelicula, Perfil
from app.services.tiempo import hoy_madrid
from main import app

if engine.url.host not in ("db", "localhost", "127.0.0.1"):
    sys.exit(f"Me niego: la BD no es local (host {engine.url.host!r})")

subprocess.run(["alembic", "upgrade", "head"], cwd=BACKEND, check=True)


def llamar(metodo, ruta, cuerpo=None):
    """Petición HTTP a la app por ASGI; devuelve (status, json o None)."""
    ruta, _, query = ruta.partition("?")
    body = json.dumps(cuerpo).encode() if cuerpo is not None else b""
    scope = {"type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1", "method": metodo, "scheme": "http",
             "path": ruta, "raw_path": ruta.encode(), "query_string": query.encode(), "root_path": "",
             "headers": [(b"content-type", b"application/json")], "client": ("test", 1), "server": ("test", 80)}
    mensajes = [{"type": "http.request", "body": body, "more_body": False}]
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


A, B = uuid.uuid4(), uuid.uuid4()
actual = {"id": A}
app.dependency_overrides[usuario_actual] = lambda: Usuario(id=str(actual["id"]), email=None)


def como(usuario):
    actual["id"] = usuario


def ok(esperado, resultado, que):
    codigo, cuerpo = resultado
    assert codigo == esperado, (que, codigo, cuerpo)
    print(f"OK: {que} -> {codigo}")
    return cuerpo


hoy = hoy_madrid()
dia = lambda n: str(hoy - timedelta(days=n))

with Session(engine) as session:
    p1, p2 = session.exec(select(Pelicula.id).order_by(Pelicula.id).limit(2)).all()
    pase = session.exec(select(Pase).where(Pase.fecha_hora < datetime.combine(hoy + timedelta(days=1), time()))
                        .order_by(Pase.activo, Pase.fecha_hora.desc())).first()  # un inactivo si lo hay
    pase = pase and dict(id=pase.id, pelicula_id=pase.pelicula_id, fecha=pase.fecha_hora.date(), slug=pase.cine_rel.slug,
                         activo=pase.activo)

# Con perfil (nombre de usuario): sin él, usuario_con_nombre cierra estos endpoints
with Session(engine) as session:
    session.add_all(Perfil(user_id=u, usuario=f"chk_{u.hex[:12]}") for u in [A, B])
    session.commit()

try:
    # --- Crear, listar, editar, borrar (usuario A) ---
    como(A)
    e1 = ok(201, llamar("POST", "/diario", {"pelicula_id": p1, "fecha_vista": dia(10), "nota": 7, "comentario": "  hola  "}), "crear")
    assert e1["comentario"] == "hola" and e1["nota"] == 7 and e1["cine"] is None and e1["repeticion"] is False, e1
    assert e1["pelicula"]["id"] == p1 and set(e1["pelicula"]) == {"id", "titulo", "poster_url", "anio", "director", "nota_tmdb"}
    assert "user_id" not in e1
    detalle = ok(409, llamar("POST", "/diario", {"pelicula_id": p1, "fecha_vista": dia(10)}), "duplicado")["detail"]
    assert "mismo día" in detalle, detalle
    e2 = ok(201, llamar("POST", "/diario", {"pelicula_id": p1, "fecha_vista": dia(5), "repeticion": True}), "misma película otro día")
    e3 = ok(201, llamar("POST", "/diario", {"pelicula_id": p2, "fecha_vista": dia(3), "cine_slug": "dore"}), "crear con cine")
    assert e3["cine"] == {"slug": "dore", "nombre": "Cine Doré"}, e3["cine"]

    lista = ok(200, llamar("GET", "/diario"), "listar")
    assert lista["total"] == 3 and [e["id"] for e in lista["entradas"]] == [e3["id"], e2["id"], e1["id"]], lista
    pag = ok(200, llamar("GET", "/diario?limite=2&desplazamiento=0"), "página 1")
    assert pag["total"] == 3 and [e["id"] for e in pag["entradas"]] == [e3["id"], e2["id"]]
    pag = ok(200, llamar("GET", "/diario?limite=2&desplazamiento=2"), "página 2")
    assert pag["total"] == 3 and [e["id"] for e in pag["entradas"]] == [e1["id"]]
    ok(422, llamar("GET", "/diario?limite=0"), "límite 0")
    ok(422, llamar("GET", "/diario?desplazamiento=-1"), "desplazamiento negativo")
    # Mismo día: manda creado_en desc (aquí el id, que crece con él)
    e4 = ok(201, llamar("POST", "/diario", {"pelicula_id": p2, "fecha_vista": dia(5)}), "otra del mismo día")
    assert [e["id"] for e in ok(200, llamar("GET", "/diario"), "orden")["entradas"]] == [e3["id"], e4["id"], e2["id"], e1["id"]]

    de_p1 = ok(200, llamar("GET", f"/diario/pelicula/{p1}"), "entradas de una película")
    assert [e["id"] for e in de_p1] == [e2["id"], e1["id"]], de_p1

    ed = ok(200, llamar("PATCH", f"/diario/{e1['id']}", {"nota": 9, "comentario": None, "cine_slug": "verdi"}), "editar")
    assert ed["nota"] == 9 and ed["comentario"] is None and ed["cine"]["slug"] == "verdi" and ed["fecha_vista"] == dia(10), ed
    assert ed["actualizado_en"] > e1["actualizado_en"], (ed["actualizado_en"], e1["actualizado_en"])
    ed = ok(200, llamar("PATCH", f"/diario/{e1['id']}", {"cine_slug": None, "repeticion": True}), "quitar cine")
    assert ed["cine"] is None and ed["repeticion"] is True and ed["nota"] == 9, ed
    ok(409, llamar("PATCH", f"/diario/{e2['id']}", {"fecha_vista": dia(10)}), "editar a un día duplicado")

    # --- Validaciones ---
    manana = str(hoy + timedelta(days=1))
    ok(422, llamar("POST", "/diario", {"pelicula_id": p2, "fecha_vista": manana}), "fecha futura")
    ok(422, llamar("PATCH", f"/diario/{e1['id']}", {"fecha_vista": manana}), "editar a fecha futura")
    ok(422, llamar("PATCH", f"/diario/{e1['id']}", {"fecha_vista": None}), "fecha_vista null")
    ok(422, llamar("PATCH", f"/diario/{e1['id']}", {"repeticion": None}), "repeticion null")
    for nota in (0, 11, -1):
        ok(422, llamar("POST", "/diario", {"pelicula_id": p2, "fecha_vista": dia(1), "nota": nota}), f"nota {nota}")
    ok(422, llamar("PATCH", f"/diario/{e1['id']}", {"nota": 11}), "editar nota 11")
    ok(422, llamar("POST", "/diario", {"pelicula_id": p2, "fecha_vista": dia(1), "comentario": "x" * 2001}), "comentario de 2001")
    ok(422, llamar("PATCH", f"/diario/{e1['id']}", {"comentario": "x" * 2001}), "editar comentario de 2001")
    largo = ok(200, llamar("PATCH", f"/diario/{e1['id']}", {"comentario": "   " + "x" * 2000 + "   "}), "2000 + espacios")
    assert largo["comentario"] == "x" * 2000
    ok(422, llamar("POST", "/diario", {"pelicula_id": p2, "fecha_vista": dia(1), "cine_slug": "no-existe"}), "cine inexistente")
    ok(422, llamar("PATCH", f"/diario/{e1['id']}", {"cine_slug": "no-existe"}), "editar a cine inexistente")
    ok(422, llamar("POST", "/diario", {"pelicula_id": 0, "fecha_vista": dia(1)}), "película inexistente")
    ok(422, llamar("POST", "/diario", {"pelicula_id": p2, "fecha_vista": dia(1), "pase_id": 0}), "pase inexistente")
    ignorado = ok(201, llamar("POST", "/diario", {"pelicula_id": p2, "fecha_vista": dia(1), "user_id": str(B)}), "user_id del cliente")
    como(B)
    assert ok(200, llamar("GET", "/diario"), "B no recibe la entrada con su user_id")["total"] == 0
    como(A)
    ok(204, llamar("DELETE", f"/diario/{ignorado['id']}"), "era de A")

    # --- Aislamiento: B no ve, edita ni borra lo de A ---
    como(B)
    assert ok(200, llamar("GET", "/diario"), "B lista")["total"] == 0
    assert ok(200, llamar("GET", f"/diario/pelicula/{p1}"), "B por película") == []
    ok(404, llamar("PATCH", f"/diario/{e1['id']}", {"nota": 1}), "B edita la de A")
    ok(404, llamar("DELETE", f"/diario/{e1['id']}"), "B borra la de A")
    ok(404, llamar("PATCH", "/diario/999999999", {"nota": 1}), "id inexistente (mismo 404)")
    ok(201, llamar("POST", "/diario", {"pelicula_id": p1, "fecha_vista": dia(10)}), "B, misma película y día que A")
    como(A)
    assert ok(200, llamar("GET", f"/diario/pelicula/{p1}"), "A sigue igual")[-1]["nota"] == 9

    ok(204, llamar("DELETE", f"/diario/{e1['id']}"), "borrar")
    ok(404, llamar("DELETE", f"/diario/{e1['id']}"), "borrar otra vez")
    assert ok(200, llamar("GET", "/diario"), "tras borrar")["total"] == 3

    # --- Con un pase real: el pase fija el cine ---
    if pase:
        como(B)
        cuerpo = {"pelicula_id": pase["pelicula_id"], "fecha_vista": str(pase["fecha"]), "pase_id": pase["id"]}
        con_pase = ok(201, llamar("POST", "/diario", cuerpo), "crear con pase")
        assert con_pase["pase_id"] == pase["id"] and con_pase["cine"]["slug"] == pase["slug"], con_pase
        ok(422, llamar("POST", "/diario", {**cuerpo, "fecha_vista": str(pase["fecha"] - timedelta(days=1))}), "pase de otro día")
        otro = "dore" if pase["slug"] != "dore" else "verdi"
        ok(422, llamar("POST", "/diario", {**cuerpo, "fecha_vista": str(pase["fecha"] - timedelta(days=2)), "cine_slug": otro}), "pase de otro cine")
        cambiada = ok(200, llamar("PATCH", f"/diario/{con_pase['id']}", {"fecha_vista": str(pase["fecha"] - timedelta(days=3))}), "cambiar el día suelta el pase")
        assert cambiada["pase_id"] is None
        como(A)

    # --- Sin token: 401 (sin override y con SUPABASE_URL, para no depender del entorno) ---
    app.dependency_overrides.clear()
    url_antes, auth.SUPABASE_URL = auth.SUPABASE_URL, "https://prueba.supabase.co"
    try:
        for metodo, ruta, cuerpo in [("GET", "/diario", None), ("POST", "/diario", {"pelicula_id": p1, "fecha_vista": dia(1)}),
                                     ("PATCH", f"/diario/{e2['id']}", {"nota": 1}), ("DELETE", f"/diario/{e2['id']}", None),
                                     ("GET", f"/diario/pelicula/{p1}", None)]:
            ok(401, llamar(metodo, ruta, cuerpo), f"sin token {metodo} {ruta}")

        # --- /pelicula/{id}/cines (público): contra la consulta directa ---
        if pase:
            cines = ok(200, llamar("GET", f"/pelicula/{pase['pelicula_id']}/cines?fecha={pase['fecha']}"), "cines del día (sin token)")
            with Session(engine) as session:
                inicio = datetime.combine(pase["fecha"], time())
                pases = session.exec(select(Pase).where(Pase.pelicula_id == pase["pelicula_id"], Pase.fecha_hora >= inicio,
                                                        Pase.fecha_hora < inicio + timedelta(days=1))).all()
                esperado = {(p.cine_rel.slug, p.fecha_hora.strftime("%H:%M")) for p in pases}
                hay_inactivos = any(not p.activo for p in pases)
            assert {(c["slug"], h) for c in cines for h in c["horas"]} == esperado, (cines, esperado)
            assert len({c["slug"] for c in cines}) == len(cines) and all(c["horas"] == sorted(c["horas"]) for c in cines)
            assert pase["slug"] in {c["slug"] for c in cines}
            assert hay_inactivos or pase["activo"]  # si en la BD hay inactivos, el elegido lo es y sale
            print(f"OK: {len(cines)} cines, {len(esperado)} horas ({'con' if hay_inactivos else 'sin'} pases inactivos)")
        else:
            print("AVISO: no hay pases en la BD local; /pelicula/{id}/cines solo se prueba vacío")
        assert ok(200, llamar("GET", f"/pelicula/{p1}/cines?fecha=1990-01-01"), "día sin pases") == []
        ok(404, llamar("GET", "/pelicula/0/cines?fecha=2026-01-01"), "película inexistente")
        ok(422, llamar("GET", f"/pelicula/{p1}/cines"), "sin fecha")
    finally:
        auth.SUPABASE_URL = url_antes

    # --- La tabla: RLS, permisos en Supabase (simulado) y CHECK en la BD ---
    spec = importlib.util.spec_from_file_location("m0010", BACKEND / "migrations/versions/0010_diario_entrada.py")
    m0010 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m0010)
    with engine.connect() as conn:
        assert conn.execute(text("SELECT relrowsecurity FROM pg_class WHERE oid = 'public.diario_entrada'::regclass")).scalar()
        print("OK: diario_entrada tiene RLS activado")
        try:
            for rol in ("anon", "authenticated"):
                if not conn.execute(text("SELECT 1 FROM pg_roles WHERE rolname = :r"), {"r": rol}).scalar():
                    conn.execute(text(f"CREATE ROLE {rol} NOLOGIN"))
            conn.execute(text("GRANT ALL ON public.diario_entrada, public.diario_entrada_id_seq TO anon, authenticated"))
            conn.execute(text(m0010.SQL_RLS))
            for rol in ("anon", "authenticated"):
                assert not conn.execute(text("SELECT has_table_privilege(:r, 'public.diario_entrada', 'SELECT')"), {"r": rol}).scalar(), rol
                assert not conn.execute(text("SELECT has_sequence_privilege(:r, 'public.diario_entrada_id_seq', 'USAGE')"), {"r": rol}).scalar(), rol
            print("OK: anon/authenticated sin permisos en diario_entrada ni en su secuencia")
        finally:
            conn.rollback()
    for valores, que in [({"nota": 11}, "nota"), ({"nota": 0}, "nota"), ({"comentario": "x" * 2001}, "comentario")]:
        with Session(engine) as session:
            session.add(DiarioEntrada(user_id=A, pelicula_id=p1, fecha_vista=hoy, **valores))
            try:
                session.commit()
                raise AssertionError(f"la BD debería rechazar {valores}")
            except IntegrityError as e:
                assert f"ck_diario_entrada_{que}" in str(e.orig), e
    print("OK: los CHECK de nota y comentario también están en la BD")
finally:
    app.dependency_overrides.clear()
    with Session(engine) as session:
        session.exec(delete(Perfil).where(Perfil.user_id.in_([A, B])))
        borradas = session.exec(delete(DiarioEntrada).where(DiarioEntrada.user_id.in_([A, B]))).rowcount
        session.commit()
        quedan = session.exec(select(DiarioEntrada).where(DiarioEntrada.user_id.in_([A, B]))).all()
    assert not quedan
    print(f"Limpieza: {borradas} entradas de prueba borradas")

print("TODO OK: check_diario")
