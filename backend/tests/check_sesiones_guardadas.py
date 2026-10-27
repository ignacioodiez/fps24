"""Self-check de las sesiones guardadas (migración 0019 y app/sesiones.py) contra la BD local. Sin red.
Uso: docker compose exec api python tests/check_sesiones_guardadas.py
Llama a la app por ASGI con el cliente mínimo de check_diario.py (TestClient necesita httpx, que no está instalado),
con usuario_actual sustituido por usuarios de prueba. Crea un cine de prueba (chk-ses-*) con sus pases sobre películas
existentes y lo borra al final con todo lo de los usuarios de prueba; no borra películas ni datos de nadie más."""
import asyncio
import importlib.util
import json
import subprocess
import sys
import threading
import uuid
from datetime import datetime, time, timedelta
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, delete, func, select

from app import sesiones as modulo
from app.auth import Usuario, usuario_actual
from app.database.engine import engine
from app.database.models import Cine, DiarioEntrada, Pase, Pelicula, SesionGuardada
from app.services.tiempo import ahora_madrid
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


def ok(esperado, resultado, que):
    codigo, cuerpo = resultado
    assert codigo == esperado, (que, codigo, cuerpo)
    print(f"OK: {que} -> {codigo}")
    return cuerpo


A, B = uuid.uuid4(), uuid.uuid4()
PRUEBA = [A, B]
SLUG = f"chk-ses-{uuid.uuid4().hex[:6]}"
actual = {"id": A}


def como(usuario):
    actual["id"] = usuario


def guardar(pase_id, **extra):
    return llamar("POST", "/me/sesiones", {"sesion_id": pase_id, **extra})


def contar(modelo, *donde):
    with Session(engine) as session:
        return session.exec(select(func.count()).select_from(modelo).where(*donde)).one()


ahora = ahora_madrid().replace(second=0, microsecond=0)
# Madrid va por delante de UTC: "hace 30 min" en Madrid aún sería futuro en UTC. Así se ve que manda la hora de Madrid.
CUANDO = {"futura": ahora + timedelta(days=2, hours=1), "pronto": ahora + timedelta(minutes=30),
          "hace_media_hora": ahora - timedelta(minutes=30), "ayer": ahora - timedelta(days=1),
          "borrable": ahora + timedelta(days=3), "inactiva": ahora + timedelta(days=4)}

try:
    with Session(engine) as session:
        p1, p2 = session.exec(select(Pelicula).order_by(Pelicula.id).limit(2)).all()
        p1, p2, titulo1 = p1.id, p2.id, p1.titulo
        cine = Cine(slug=SLUG, nombre="Cine de prueba sesiones")
        session.add(cine)
        session.commit()
        pases = {}
        for nombre, cuando in CUANDO.items():
            pase = Pase(cine_id=cine.id, pelicula_id=p2 if nombre == "ayer" else p1, fecha_hora=cuando, idioma="VOSE",
                        link_compra=f"https://ejemplo.es/{nombre}", precio="7 €", activo=nombre != "inactiva")
            session.add(pase)
            session.commit()
            pases[nombre] = pase.id
        cine_id = cine.id

    # --- Sin sesión: 401 (o 503 si falta SUPABASE_URL) ---
    for metodo, ruta in [("GET", "/me/sesiones"), ("GET", "/me/sesiones/ids"), ("POST", "/me/sesiones"),
                         ("DELETE", "/me/sesiones/1"), ("POST", "/me/sesiones/1/vista")]:
        assert llamar(metodo, ruta, {"sesion_id": pases["futura"]} if metodo == "POST" else None)[0] in (401, 503), ruta
    print("OK: sin sesión, 401")
    app.dependency_overrides[usuario_actual] = lambda: Usuario(id=str(actual["id"]), email=None)

    # --- /pelicula/{id} trae el id de cada pase (lo que el front manda a POST /me/sesiones) ---
    detalle = ok(200, llamar("GET", f"/pelicula/{p1}"), "ficha de película")
    assert pases["futura"] in [p["id"] for p in detalle["pases"]], detalle["pases"]

    # --- Guardar: copia desde la BD, sin fiarse del cliente; idempotente ---
    g = ok(200, guardar(pases["futura"], titulo="Trampa", user_id=str(B), link_compra="https://malo.es"), "guardar")
    assert g["titulo"] == titulo1 and g["cine_slug"] == SLUG and g["cine_nombre"] == "Cine de prueba sesiones", g
    assert g["fecha"] == str(CUANDO["futura"].date()) and g["hora"] == CUANDO["futura"].strftime("%H:%M:%S"), g
    assert g["idioma"] == "VOSE" and g["link_compra"] == "https://ejemplo.es/futura" and g["sesion_id"] == pases["futura"], g
    assert g["pelicula_id"] == p1 and g["diario_entrada_id"] is None and "user_id" not in g, g
    otra_vez = ok(200, guardar(pases["futura"]), "guardar otra vez (idempotente)")
    assert otra_vez["id"] == g["id"] and contar(SesionGuardada, SesionGuardada.user_id == A) == 1
    ok(404, guardar(0), "sesión inexistente")
    ok(404, guardar(pases["inactiva"]), "sesión retirada por el scraper (inactiva)")
    ok(422, llamar("POST", "/me/sesiones", {}), "sin sesion_id")

    # Dos a la vez: una sola guardada y ningún error
    def a_la_vez(pase_id, n=3):
        barrera, errores = threading.Barrier(n), []

        def una():
            with Session(engine) as session:
                barrera.wait()
                try:
                    modulo.guardar_sesion(modulo.Guardar(sesion_id=pase_id), Usuario(id=str(A), email=None), session)
                except Exception as e:  # noqa: BLE001
                    errores.append(e)

        hilos = [threading.Thread(target=una) for _ in range(n)]
        for h in hilos:
            h.start()
        for h in hilos:
            h.join()
        return errores

    assert a_la_vez(pases["pronto"]) == []
    assert contar(SesionGuardada, SesionGuardada.user_id == A, SesionGuardada.pase_id == pases["pronto"]) == 1
    print("OK: guardar a la vez, sin error ni duplicado")

    for nombre in ("hace_media_hora", "ayer", "borrable"):
        ok(200, guardar(pases[nombre]), f"guardar {nombre}")

    # --- Próximas y pasadas con la hora de Madrid ---
    agenda = ok(200, llamar("GET", "/me/sesiones"), "agenda")
    por_pase = lambda lista: [x["sesion_id"] for x in lista]
    assert por_pase(agenda["proximas"]) == [pases["pronto"], pases["futura"], pases["borrable"]], agenda["proximas"]
    assert por_pase(agenda["pasadas"]) == [pases["hace_media_hora"], pases["ayer"]], agenda["pasadas"]
    marcas = ok(200, llamar("GET", "/me/sesiones/ids"), "ids")
    assert {m["sesion_id"] for m in marcas} == {pases[n] for n in ("pronto", "futura", "borrable", "hace_media_hora")} - (
        set() if CUANDO["hace_media_hora"].date() == ahora.date() else {pases["hace_media_hora"]}), marcas  # de hoy en adelante
    assert all(set(m) == {"id", "sesion_id"} for m in marcas), marcas

    # --- La copia sobrevive al borrado del pase original ---
    with Session(engine) as session:
        session.delete(session.get(Pase, pases["borrable"]))
        session.commit()
    copia = next(x for x in ok(200, llamar("GET", "/me/sesiones"), "agenda tras borrar el pase")["proximas"]
                 if x["fecha"] == str(CUANDO["borrable"].date()))
    assert copia["sesion_id"] is None and copia["titulo"] == titulo1 and copia["link_compra"] == "https://ejemplo.es/borrable", copia
    assert copia["id"] not in [m["id"] for m in ok(200, llamar("GET", "/me/sesiones/ids"), "ids tras borrar")]
    print("OK: la copia sigue entera sin el pase (y sin marca en la cartelera)")

    # --- "La vi": una única entrada de diario, idempotente ---
    agenda = ok(200, llamar("GET", "/me/sesiones"), "agenda")
    pasada = next(x for x in agenda["pasadas"] if x["sesion_id"] == pases["hace_media_hora"])
    ok(422, llamar("POST", f"/me/sesiones/{agenda['proximas'][0]['id']}/vista"), "La vi en una futura")
    vista = ok(200, llamar("POST", f"/me/sesiones/{pasada['id']}/vista"), "La vi")
    assert vista["diario_entrada_id"], vista
    assert ok(200, llamar("POST", f"/me/sesiones/{pasada['id']}/vista"), "La vi otra vez")["diario_entrada_id"] == vista["diario_entrada_id"]
    with Session(engine) as session:
        entradas = session.exec(select(DiarioEntrada).where(DiarioEntrada.user_id == A)).all()
        assert len(entradas) == 1, entradas
        e = entradas[0]
        assert (e.pelicula_id, e.fecha_vista, e.cine_id, e.pase_id) == (p1, CUANDO["hace_media_hora"].date(), cine_id,
                                                                         pases["hace_media_hora"]), e
    # Si ya estaba apuntada a mano ese día, se enlaza esa y no se crea otra
    ayer = next(x for x in agenda["pasadas"] if x["sesion_id"] == pases["ayer"])
    a_mano = ok(201, llamar("POST", "/diario", {"pelicula_id": p2, "fecha_vista": ayer["fecha"]}), "apuntada a mano")
    assert ok(200, llamar("POST", f"/me/sesiones/{ayer['id']}/vista"), "La vi con entrada previa")["diario_entrada_id"] == a_mano["id"]
    assert contar(DiarioEntrada, DiarioEntrada.user_id == A) == 2
    # Sin película (la borraron: SET NULL) -> error claro
    with Session(engine) as session:
        session.get(SesionGuardada, ayer["id"]).pelicula_id = None
        session.get(SesionGuardada, ayer["id"]).diario_entrada_id = None
        session.commit()
    detalle = ok(422, llamar("POST", f"/me/sesiones/{ayer['id']}/vista"), "La vi sin película")["detail"]
    assert "película" in detalle, detalle
    # Borrar la entrada del diario desmarca la sesión (SET NULL), no la borra
    ok(204, llamar("DELETE", f"/diario/{vista['diario_entrada_id']}"), "borrar la entrada del diario")
    assert next(x for x in ok(200, llamar("GET", "/me/sesiones"), "agenda")["pasadas"] if x["id"] == pasada["id"])["diario_entrada_id"] is None

    # --- Aislamiento entre usuarios ---
    como(B)
    assert ok(200, llamar("GET", "/me/sesiones"), "B no ve las de A") == {"proximas": [], "pasadas": []}
    assert ok(200, llamar("GET", "/me/sesiones/ids"), "B sin ids") == []
    ok(404, llamar("POST", f"/me/sesiones/{pasada['id']}/vista"), "B no marca vista la de A")
    ok(204, llamar("DELETE", f"/me/sesiones/{g['id']}"), "B 'quita' la de A (no toca nada)")
    de_b = ok(200, guardar(pases["futura"]), "B guarda la misma sesión")
    assert de_b["id"] != g["id"]
    assert contar(SesionGuardada, SesionGuardada.id == g["id"]) == 1 and contar(DiarioEntrada, DiarioEntrada.user_id == B) == 0
    como(A)
    assert len(ok(200, llamar("GET", "/me/sesiones"), "A sigue igual")["proximas"]) == 3
    print("OK: cada usuario solo ve y toca las suyas")

    # --- Quitar, idempotente ---
    ok(204, llamar("DELETE", f"/me/sesiones/{g['id']}"), "quitar")
    ok(204, llamar("DELETE", f"/me/sesiones/{g['id']}"), "quitar otra vez")
    assert contar(SesionGuardada, SesionGuardada.id == g["id"]) == 0 and contar(SesionGuardada, SesionGuardada.id == de_b["id"]) == 1

    # --- Tope: con TOPE guardadas no entra otra, pero repetir una ya guardada sigue valiendo ---
    with Session(engine) as session:
        faltan = modulo.TOPE - contar(SesionGuardada, SesionGuardada.user_id == A)
        for i in range(faltan):
            session.add(SesionGuardada(user_id=A, titulo=f"Relleno {i}", cine_nombre="Cine de prueba sesiones", cine_slug=SLUG,
                                       fecha=ahora.date() - timedelta(days=30), hora=time(0, 0)))
        session.commit()
    detalle = ok(409, guardar(pases["futura"]), "por encima del tope")["detail"]
    assert str(modulo.TOPE) in detalle, detalle
    ok(200, guardar(pases["pronto"]), "repetir una guardada con el tope lleno")
    assert contar(SesionGuardada, SesionGuardada.user_id == A) == modulo.TOPE

    # --- La tabla: único, FK y RLS/REVOKE ---
    with Session(engine) as session:
        session.add(SesionGuardada(user_id=A, titulo="Relleno 0", cine_nombre="Cine de prueba sesiones", cine_slug=SLUG,
                                   fecha=ahora.date() - timedelta(days=30), hora=time(0, 0)))
        try:
            session.commit()
            raise AssertionError("la BD debería rechazar el duplicado")
        except IntegrityError as e:
            assert "uq_sesion_guardada_usuario_sesion" in str(e.orig), e
    print("OK: único (user_id, cine_nombre, fecha, hora, titulo) en la BD")

    spec = importlib.util.spec_from_file_location("m0019", BACKEND / "migrations/versions/0019_sesion_guardada.py")
    m0019 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m0019)
    with engine.connect() as conn:
        rls, force = conn.execute(text("SELECT relrowsecurity, relforcerowsecurity FROM pg_class "
                                       "WHERE oid = 'public.sesion_guardada'::regclass")).one()
        assert rls and not force, (rls, force)
        try:
            for rol in ("anon", "authenticated"):
                if not conn.execute(text("SELECT 1 FROM pg_roles WHERE rolname = :r"), {"r": rol}).scalar():
                    conn.execute(text(f"CREATE ROLE {rol} NOLOGIN"))
            conn.execute(text("GRANT ALL ON public.sesion_guardada TO anon, authenticated"))
            conn.execute(text("GRANT ALL ON SEQUENCE public.sesion_guardada_id_seq TO anon, authenticated"))
            conn.execute(text(m0019.SQL_RLS))
            for rol in ("anon", "authenticated"):
                for permiso in ("SELECT", "INSERT", "UPDATE", "DELETE"):
                    assert not conn.execute(text("SELECT has_table_privilege(:r, 'public.sesion_guardada', :p)"),
                                            {"r": rol, "p": permiso}).scalar(), (rol, permiso)
                assert not conn.execute(text("SELECT has_sequence_privilege(:r, 'public.sesion_guardada_id_seq', 'USAGE')"),
                                        {"r": rol}).scalar(), rol
            print("OK: sesion_guardada con RLS (sin FORCE) y sin permisos para anon/authenticated")
        finally:
            conn.rollback()
finally:
    app.dependency_overrides.clear()
    with Session(engine) as session:
        session.exec(delete(SesionGuardada).where(SesionGuardada.user_id.in_(PRUEBA)))
        session.exec(delete(DiarioEntrada).where(DiarioEntrada.user_id.in_(PRUEBA)))
        session.exec(delete(Pase).where(Pase.cine_id.in_(select(Cine.id).where(Cine.slug == SLUG))))
        session.exec(delete(Cine).where(Cine.slug == SLUG))
        session.commit()
        assert not session.exec(select(SesionGuardada).where(SesionGuardada.user_id.in_(PRUEBA))).all()
    print("Limpieza: sesiones, diario, pases y cine de prueba borrados")

print("TODO OK: check_sesiones_guardadas")
