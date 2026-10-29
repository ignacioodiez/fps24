"""Self-check de los cines favoritos (migración 0013 y app/favoritos.py) contra la BD local. Sin red.
Uso: docker compose exec api python tests/check_cines_favoritos.py
Llama a la app por ASGI con el cliente mínimo de check_diario.py (TestClient necesita httpx, que no está instalado),
con usuario_actual sustituido por usuarios de prueba. Solo crea cines de prueba (chk-fav-*) y favoritos de usuarios
de prueba, y los borra al final; no toca películas, pases ni diario."""
import asyncio
import importlib.util
import json
import subprocess
import sys
import threading
import uuid
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, delete, select

from app import favoritos as modulo
from app.auth import Usuario, usuario_actual
from app.database.engine import engine
from app.database.models import Cine, CineFavorito, Perfil
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
sufijo = uuid.uuid4().hex[:6]
SLUGS = [f"chk-fav-{sufijo}-{i}" for i in range(3)]
actual = {"id": A}


def con_sesion():
    app.dependency_overrides[usuario_actual] = lambda: Usuario(id=str(actual["id"]), email="a@ejemplo.es")


def como(usuario):
    actual["id"] = usuario


def favoritos_en_bd(uid):
    with Session(engine) as session:
        return set(session.exec(select(Cine.slug).join(CineFavorito, CineFavorito.cine_id == Cine.id)
                                .where(CineFavorito.user_id == uid)).all())


with Session(engine) as session:
    for i, slug in enumerate(SLUGS):
        session.add(Cine(slug=slug, nombre=f"Cine de prueba {i}"))
    session.commit()
    ids = {c.slug: c.id for c in session.exec(select(Cine).where(Cine.slug.in_(SLUGS))).all()}
uno, dos, tres = SLUGS

# Con perfil (nombre de usuario): sin él, usuario_con_nombre cierra estos endpoints
with Session(engine) as session:
    session.add_all(Perfil(user_id=u, usuario=f"chk_{u.hex[:12]}") for u in PRUEBA)
    session.commit()

try:
    # --- Sin sesión: los tres responden 401 (o 503 si falta SUPABASE_URL) y no tocan nada ---
    for metodo in ("GET", "PUT", "DELETE"):
        ruta = "/me/cines-favoritos" + ("" if metodo == "GET" else f"/{uno}")
        assert llamar(metodo, ruta)[0] in (401, 503), metodo
    assert favoritos_en_bd(A) == set()
    print("OK: sin sesión, 401")
    con_sesion()

    # --- Añadir, idempotente; 404 si el cine no existe; lista en orden de alta ---
    assert ok(200, llamar("GET", "/me/cines-favoritos"), "vacío") == []
    ok(204, llamar("PUT", f"/me/cines-favoritos/{dos}"), "añadir dos")
    ok(204, llamar("PUT", f"/me/cines-favoritos/{uno}"), "añadir uno")
    ok(204, llamar("PUT", f"/me/cines-favoritos/{uno}"), "añadir uno otra vez (idempotente)")
    assert ok(200, llamar("GET", "/me/cines-favoritos"), "leer") == [dos, uno]
    assert ok(404, llamar("PUT", f"/me/cines-favoritos/no-existe-{sufijo}"), "cine inexistente")["detail"] == "Cine no encontrado"
    assert favoritos_en_bd(A) == {uno, dos}

    # --- Quitar, idempotente (también si el cine no existe) ---
    ok(204, llamar("DELETE", f"/me/cines-favoritos/{dos}"), "quitar dos")
    ok(204, llamar("DELETE", f"/me/cines-favoritos/{dos}"), "quitar dos otra vez (idempotente)")
    ok(204, llamar("DELETE", f"/me/cines-favoritos/no-existe-{sufijo}"), "quitar cine inexistente")
    assert ok(200, llamar("GET", "/me/cines-favoritos"), "leer tras quitar") == [uno]

    # --- Otro usuario no ve ni toca los míos ---
    como(B)
    assert ok(200, llamar("GET", "/me/cines-favoritos"), "B no ve los de A") == []
    ok(204, llamar("DELETE", f"/me/cines-favoritos/{uno}"), "B quita 'uno' (de su lista, vacía)")
    ok(204, llamar("PUT", f"/me/cines-favoritos/{tres}"), "B añade tres")
    assert favoritos_en_bd(A) == {uno} and favoritos_en_bd(B) == {tres}
    como(A)
    assert ok(200, llamar("GET", "/me/cines-favoritos"), "A sigue igual") == [uno]
    print("OK: cada usuario solo ve y toca los suyos")

    # --- Carrera: el mismo PUT dos veces a la vez, un solo favorito y ningún error ---
    def a_la_vez(n=2):
        barrera, errores = threading.Barrier(n), []

        def una():
            with Session(engine) as session:
                barrera.wait()
                try:
                    modulo.anadir_favorito(dos, Usuario(id=str(A), email=None), session)
                except Exception as e:  # noqa: BLE001
                    errores.append(e)

        hilos = [threading.Thread(target=una) for _ in range(n)]
        for h in hilos:
            h.start()
        for h in hilos:
            h.join()
        return errores

    for _ in range(5):
        assert a_la_vez() == []
        with Session(engine) as session:
            filas = session.exec(select(CineFavorito).where(CineFavorito.user_id == A, CineFavorito.cine_id == ids[dos])).all()
            assert len(filas) == 1, filas
    print("OK: PUT a la vez, sin error ni duplicado")

    # --- Cascada: borrar el cine borra sus favoritos (de todos) ---
    como(B)
    ok(204, llamar("PUT", f"/me/cines-favoritos/{uno}"), "B añade uno")
    with Session(engine) as session:
        session.delete(session.get(Cine, ids[uno]))
        session.commit()
    assert uno not in favoritos_en_bd(A) and uno not in favoritos_en_bd(B)
    assert ok(200, llamar("GET", "/me/cines-favoritos"), "B tras borrar el cine") == [tres]
    print("OK: ON DELETE CASCADE")

    # --- La tabla: PK, FK y RLS/REVOKE ---
    for valores, restriccion in [(dict(user_id=A, cine_id=ids[dos]), "cine_favorito_pkey"),
                                 (dict(user_id=A, cine_id=-1), "cine_favorito_cine_id_fkey")]:
        with Session(engine) as session:
            session.add(CineFavorito(**valores))
            try:
                session.commit()
                raise AssertionError(f"la BD debería rechazar {valores}")
            except IntegrityError as e:
                assert restriccion in str(e.orig), e
    print("OK: PK (user_id, cine_id) y FK a cine en la BD")

    spec = importlib.util.spec_from_file_location("m0013", BACKEND / "migrations/versions/0013_cine_favorito.py")
    m0013 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m0013)
    with engine.connect() as conn:
        rls, force = conn.execute(text("SELECT relrowsecurity, relforcerowsecurity FROM pg_class "
                                       "WHERE oid = 'public.cine_favorito'::regclass")).one()
        assert rls and not force, (rls, force)
        try:
            for rol in ("anon", "authenticated"):
                if not conn.execute(text("SELECT 1 FROM pg_roles WHERE rolname = :r"), {"r": rol}).scalar():
                    conn.execute(text(f"CREATE ROLE {rol} NOLOGIN"))
            conn.execute(text("GRANT ALL ON public.cine_favorito TO anon, authenticated"))
            conn.execute(text(m0013.SQL_RLS))
            for rol in ("anon", "authenticated"):
                for permiso in ("SELECT", "INSERT", "DELETE"):
                    assert not conn.execute(text("SELECT has_table_privilege(:r, 'public.cine_favorito', :p)"),
                                            {"r": rol, "p": permiso}).scalar(), (rol, permiso)
            print("OK: cine_favorito con RLS (sin FORCE) y sin permisos para anon/authenticated")
        finally:
            conn.rollback()

    # --- Los públicos no dependen del usuario y llevan cine_slug en cada pase ---
    app.dependency_overrides.clear()
    for ruta in ("/pases", "/destacadas", "/estrenos", "/especiales"):
        codigo, cuerpo = llamar("GET", ruta)
        assert codigo == 200, ruta
        pendientes = [cuerpo]
        while pendientes:
            x = pendientes.pop()
            if isinstance(x, dict):
                assert "fecha_hora" not in x or isinstance(x.get("cine_slug"), str), (ruta, x)
                pendientes.extend(x.values())
            elif isinstance(x, list):
                pendientes.extend(x)
    print("OK: /pases, /destacadas, /estrenos y /especiales sin sesión, con cine_slug en cada pase")
finally:
    app.dependency_overrides.clear()
    with Session(engine) as session:
        session.exec(delete(Perfil).where(Perfil.user_id.in_(PRUEBA)))
        session.exec(delete(CineFavorito).where(CineFavorito.user_id.in_(PRUEBA)))
        session.exec(delete(Cine).where(Cine.slug.in_(SLUGS)))
        session.commit()
        assert not session.exec(select(CineFavorito).where(CineFavorito.user_id.in_(PRUEBA))).all()
    print("Limpieza: favoritos y cines de prueba borrados")

print("TODO OK: check_cines_favoritos")
