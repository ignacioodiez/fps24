"""Self-check del panel admin (app/admin.py, migración 0014 y el filtro de ocultas en destacadas) contra la BD local.
Sin red. Uso: docker compose exec api python tests/check_admin.py
Llama a la app por ASGI con el cliente mínimo de check_diario.py (TestClient necesita httpx, que no está instalado),
con usuario_o_nada sustituido por usuarios de prueba. Crea su propio cine, dos películas, sus pases, perfiles, una
entrada de diario y un favorito de usuarios de prueba (chk-adm-*), y lo borra todo al final: no toca películas, pases
ni diario existentes."""
import asyncio
import importlib.util
import json
import logging
import os
import subprocess
import sys
import uuid
from datetime import date, datetime, time, timedelta
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from sqlalchemy import text
from sqlmodel import Session, delete, select

from app import admin
from app.auth import Usuario, usuario_actual
from app.database.engine import engine
from app.database.models import Cine, CineFavorito, DiarioEntrada, Pase, Pelicula, PeliculaOculta, Perfil
from app.services import destacadas as d
from app.services.tiempo import ahora_madrid
from main import app

if engine.url.host not in ("db", "localhost", "127.0.0.1"):
    sys.exit(f"Me niego: la BD no es local (host {engine.url.host!r})")

subprocess.run(["alembic", "upgrade", "head"], cwd=BACKEND, check=True)


def llamar(metodo, ruta, cuerpo=None, cabeceras=()):
    """Petición HTTP a la app por ASGI; devuelve (status, json o None)."""
    ruta, _, query = ruta.partition("?")
    body = json.dumps(cuerpo).encode() if cuerpo is not None else b""
    scope = {"type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1", "method": metodo, "scheme": "http",
             "path": ruta, "raw_path": ruta.encode(), "query_string": query.encode(), "root_path": "",
             "headers": [(b"content-type", b"application/json"), *cabeceras], "client": ("test", 1),
             "server": ("test", 80)}
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


sufijo = uuid.uuid4().hex[:6]
ADMIN, NORMAL, PUBLICO = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
PRUEBA = [ADMIN, NORMAL, PUBLICO]
CORREO_ADMIN = f"Admin-{sufijo}@Ejemplo.es"
SECRETO = f"comentario-secreto-{sufijo}"
actual = {"usuario": None}
app.dependency_overrides[admin.usuario_o_nada] = lambda: actual["usuario"]
app.dependency_overrides[usuario_actual] = lambda: actual["usuario"]  # para /me
os.environ["ADMIN_EMAILS"] = f" otra@ejemplo.es , {CORREO_ADMIN.upper()} "


def como(uid, email):
    actual["usuario"] = Usuario(id=str(uid), email=email)


# Los accesos admin quedan en el log, con el user_id y sin el correo
registros = []
manejador = logging.Handler()
manejador.emit = lambda r: registros.append(r.getMessage())
admin.log.addHandler(manejador)
logging.getLogger("uvicorn.error").setLevel(logging.INFO)  # como lo deja uvicorn al arrancar

# --- Datos de prueba: la semana que viene, para no depender de la hora a la que se lance ---
lunes = d.semana(ahora_madrid())[0] + timedelta(weeks=1)
ahora_lunes = datetime.combine(lunes, time(0, 1))
with Session(engine) as session:
    cine = Cine(slug=f"chk-adm-{sufijo}", nombre=f"Cine admin {sufijo}", tipo=d.TIPO_CINE_ESPECIAL)
    session.add(cine)
    estreno = Pelicula(titulo=f"Chkadmin {sufijo} estreno", tmdb_id=-int(uuid.uuid4().int % 10**9) - 1, generos="Drama",
                       nota_tmdb=9.99, votos=10**7, fecha_estreno=lunes + timedelta(days=2))
    especial = Pelicula(titulo=f"Chkadmin {sufijo} clasico", tmdb_id=-int(uuid.uuid4().int % 10**9) - 1, generos="Drama",
                        nota_tmdb=9.99, votos=10**7, fecha_estreno=date(1960, 1, 1))
    session.add_all([estreno, especial])
    session.flush()
    session.add_all([
        Pase(pelicula_id=estreno.id, cine_id=cine.id, fecha_hora=datetime.combine(lunes + timedelta(days=2), time(20))),
        Pase(pelicula_id=especial.id, cine_id=cine.id, fecha_hora=datetime.combine(lunes + timedelta(days=3), time(20)),
             es_evento_especial=True),
        Perfil(user_id=NORMAL, usuario=f"chk_adm_{sufijo}_n", visibilidad="privado"),
        Perfil(user_id=PUBLICO, usuario=f"chk_adm_{sufijo}_p", visibilidad="publico", diario_publico=True),
        DiarioEntrada(user_id=PUBLICO, pelicula_id=estreno.id, fecha_vista=date.today(), nota=8, comentario=SECRETO),
        CineFavorito(user_id=PUBLICO, cine_id=cine.id),
    ])
    session.commit()
    cine_id, E, S = cine.id, estreno.id, especial.id
PELIS = [E, S]
RUTAS = [("GET", "/admin/resumen"), ("GET", "/admin/usuarios?pagina=1"), ("GET", "/admin/peliculas/buscar?q=chkadmin"),
         ("GET", "/admin/peliculas/ocultas"), ("POST", f"/admin/peliculas/{E}/ocultar"),
         ("DELETE", f"/admin/peliculas/{E}/ocultar")]


def ids_destacadas():
    """Ids en /destacadas (la semana que viene), /estrenos?semana=1 y /especiales?semana=1."""
    with Session(engine) as session:
        r = d.leer_destacadas(session, ahora_lunes)
    estrenos = {x["pelicula"].id for x in r["estrenos"]}
    especiales = {x["pelicula"].id for x in r["especiales"]}
    pag_e = {x["pelicula"]["id"] for x in ok(200, llamar("GET", "/estrenos?semana=1"), "/estrenos?semana=1")["peliculas"]}
    pag_s = {x["pelicula"]["id"] for x in ok(200, llamar("GET", "/especiales?semana=1"), "/especiales?semana=1")["peliculas"]}
    return estrenos, especiales, pag_e, pag_s


def sigue_en_el_resto(pid, titulo):
    detalle = ok(200, llamar("GET", f"/pelicula/{pid}"), f"/pelicula/{pid}")
    assert detalle["pases"], detalle
    assert pid in {p["id"] for p in ok(200, llamar("GET", "/peliculas/buscar?q=" + titulo.replace(" ", "+")), "búsqueda pública")}
    assert pid in {p["pelicula_id"] for p in ok(200, llamar("GET", "/pases"), "/pases")}


def claves(x):
    """Todas las claves de un JSON anidado."""
    if isinstance(x, dict):
        return set(x) | set().union(*map(claves, x.values()))
    if isinstance(x, list):
        return set().union(*map(claves, x)) if x else set()
    return set()


try:
    # --- Sin sesión, con token roto y con usuario normal: el mismo 404 que una ruta que no existe ---
    inexistente = llamar("GET", f"/admin/no-existe-{sufijo}")
    assert inexistente[0] == 404
    for metodo, ruta in RUTAS:
        assert llamar(metodo, ruta) == inexistente, (metodo, ruta)
    print("OK: sin sesión, 404 como una ruta inexistente")
    del app.dependency_overrides[admin.usuario_o_nada]
    for metodo, ruta in RUTAS:
        assert llamar(metodo, ruta, cabeceras=[(b"authorization", b"Bearer basura")]) == inexistente, (metodo, ruta)
    app.dependency_overrides[admin.usuario_o_nada] = lambda: actual["usuario"]
    print("OK: token no válido, 404")
    como(NORMAL, "normal@ejemplo.es")
    for metodo, ruta in RUTAS:
        assert llamar(metodo, ruta) == inexistente, (metodo, ruta)
    assert ok(200, llamar("GET", "/me"), "/me normal")["es_admin"] is False
    como(NORMAL, None)
    assert llamar("GET", "/admin/resumen") == inexistente and llamar("GET", "/me")[1]["es_admin"] is False
    print("OK: usuario normal (con o sin email), 404 y es_admin false")
    assert any(str(NORMAL) in m and "denegado" in m for m in registros)
    assert not any(m for m in registros if "ejemplo.es" in m.lower())

    # --- Admin: el email del token, sin distinguir mayúsculas ---
    como(ADMIN, CORREO_ADMIN.lower())
    assert ok(200, llamar("GET", "/me"), "/me admin")["es_admin"] is True
    resumen = ok(200, llamar("GET", "/admin/resumen"), "resumen")
    assert set(resumen) == set(admin.Resumen.model_fields), resumen
    assert resumen["fuente_usuarios"] in ("auth.users", "perfil")
    with Session(engine) as session:
        perfiles = session.exec(text("SELECT count(*) FROM perfil")).scalar()
        assert resumen["perfiles_con_usuario"] == perfiles
        assert resumen["entradas_diario"] == session.exec(text("SELECT count(*) FROM diario_entrada")).scalar()
        assert resumen["favoritos"] == session.exec(text("SELECT count(*) FROM cine_favorito")).scalar()
        assert resumen["diarios_publicos"] == session.exec(text(
            "SELECT count(*) FROM perfil WHERE visibilidad = 'publico' AND diario_publico")).scalar()
    assert resumen["perfiles_publicos"] >= 1 and resumen["diarios_publicos"] >= 1
    if resumen["fuente_usuarios"] == "perfil":
        assert resumen["usuarios_totales"] == perfiles and resumen["altas_7_dias"] >= 2
    assert resumen["altas_7_dias"] <= resumen["altas_30_dias"] <= resumen["usuarios_totales"]
    print(f"OK: resumen ({resumen['fuente_usuarios']})")
    assert any(str(ADMIN) in m and "/admin/resumen" in m and "denegado" not in m for m in registros)
    assert not any(m for m in registros if "ejemplo.es" in m.lower())
    print("OK: log de accesos con user_id y sin correos")

    # --- Usuarios: solo los campos permitidos, nada del diario ni identificadores ---
    pagina, vistos = 1, {}
    while True:
        status, cuerpo = llamar("GET", f"/admin/usuarios?pagina={pagina}")
        assert status == 200 and len(cuerpo["usuarios"]) <= cuerpo["por_pagina"], cuerpo
        texto = json.dumps(cuerpo)
        assert SECRETO not in texto and "ejemplo.es" not in texto.lower()
        assert not any(str(u) in texto for u in PRUEBA)
        assert claves(cuerpo) == {"pagina", "por_pagina", "total", "hay_siguiente", "usuarios"} | (
            set(admin.UsuarioAdmin.model_fields) if cuerpo["usuarios"] else set()), claves(cuerpo)
        vistos.update({u["usuario"]: u for u in cuerpo["usuarios"]})
        if not cuerpo["hay_siguiente"]:
            break
        pagina += 1
    assert len(vistos) == cuerpo["total"] == perfiles
    p, n = vistos[f"chk_adm_{sufijo}_p"], vistos[f"chk_adm_{sufijo}_n"]
    assert (p["visibilidad"], p["diario_publico"], p["entradas"], p["favoritos"]) == ("publico", True, 1, 1), p
    assert (n["visibilidad"], n["diario_publico"], n["entradas"], n["favoritos"]) == ("privado", False, 0, 0), n
    assert llamar("GET", "/admin/usuarios?pagina=0")[0] == 422
    print(f"OK: usuarios en {pagina} página(s), solo recuentos")
    for metodo, ruta in RUTAS[2:4]:
        assert SECRETO not in json.dumps(llamar(metodo, ruta)[1])

    # --- Ocultar y mostrar: solo cambia /destacadas, /estrenos y /especiales ---
    estrenos, especiales, pag_e, pag_s = ids_destacadas()
    assert E in estrenos and E in pag_e and S in especiales and S in pag_s, (estrenos, especiales)
    buscadas = ok(200, llamar("GET", f"/admin/peliculas/buscar?q=chkadmin+{sufijo}"), "buscar admin")
    assert {(b["id"], b["oculta"]) for b in buscadas} == {(E, False), (S, False)}, buscadas

    ok(204, llamar("POST", f"/admin/peliculas/{E}/ocultar", {"motivo": "  prueba  "}), "ocultar estreno")
    ok(204, llamar("POST", f"/admin/peliculas/{E}/ocultar"), "ocultar otra vez, sin cuerpo (idempotente)")
    ok(204, llamar("POST", f"/admin/peliculas/{S}/ocultar", {"motivo": "prueba"}), "ocultar especial")
    assert ok(404, llamar("POST", "/admin/peliculas/-1/ocultar"), "ocultar inexistente")["detail"] == "Película no encontrada"
    assert llamar("POST", f"/admin/peliculas/{E}/ocultar", {"motivo": "x" * 501})[0] == 422
    estrenos, especiales, pag_e, pag_s = ids_destacadas()
    assert not ({E, S} & (estrenos | especiales | pag_e | pag_s))
    for pid, nombre in ((E, "estreno"), (S, "clasico")):
        sigue_en_el_resto(pid, f"chkadmin {sufijo} {nombre}")
    buscadas = ok(200, llamar("GET", f"/admin/peliculas/buscar?q=chkadmin+{sufijo}"), "buscar admin")
    assert {(b["id"], b["oculta"]) for b in buscadas} == {(E, True), (S, True)}, buscadas
    lista = {o["id"]: o for o in ok(200, llamar("GET", "/admin/peliculas/ocultas"), "ocultas")}
    assert lista[E]["motivo"] is None and lista[S]["motivo"] == "prueba", lista
    print("OK: ocultas fuera de destacadas/estrenos/especiales; siguen en /pelicula, la búsqueda y /pases")

    ok(204, llamar("DELETE", f"/admin/peliculas/{E}/ocultar"), "mostrar estreno")
    ok(204, llamar("DELETE", f"/admin/peliculas/{E}/ocultar"), "mostrar otra vez (idempotente)")
    estrenos, especiales, pag_e, pag_s = ids_destacadas()
    assert E in estrenos and E in pag_e and S not in (especiales | pag_s)
    ok(204, llamar("DELETE", f"/admin/peliculas/{S}/ocultar"), "mostrar especial")
    estrenos, especiales, pag_e, pag_s = ids_destacadas()
    assert E in estrenos and S in especiales and S in pag_s
    print("OK: mostrar las devuelve")

    # --- La tabla: RLS sin FORCE, REVOKE a anon/authenticated y ON DELETE CASCADE ---
    spec = importlib.util.spec_from_file_location("m0014", BACKEND / "migrations/versions/0014_pelicula_oculta.py")
    m0014 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m0014)
    with engine.connect() as conn:
        rls, force = conn.execute(text("SELECT relrowsecurity, relforcerowsecurity FROM pg_class "
                                       "WHERE oid = 'public.pelicula_oculta'::regclass")).one()
        assert rls and not force, (rls, force)
        try:
            for rol in ("anon", "authenticated"):
                if not conn.execute(text("SELECT 1 FROM pg_roles WHERE rolname = :r"), {"r": rol}).scalar():
                    conn.execute(text(f"CREATE ROLE {rol} NOLOGIN"))
            conn.execute(text("GRANT ALL ON public.pelicula_oculta TO anon, authenticated"))
            conn.execute(text(m0014.SQL_RLS))
            for rol in ("anon", "authenticated"):
                for permiso in ("SELECT", "INSERT", "DELETE"):
                    assert not conn.execute(text("SELECT has_table_privilege(:r, 'public.pelicula_oculta', :p)"),
                                            {"r": rol, "p": permiso}).scalar(), (rol, permiso)
            print("OK: pelicula_oculta con RLS (sin FORCE) y sin permisos para anon/authenticated")
        finally:
            conn.rollback()
finally:
    app.dependency_overrides.clear()
    admin.log.removeHandler(manejador)
    with Session(engine) as session:
        session.exec(delete(DiarioEntrada).where(DiarioEntrada.user_id.in_(PRUEBA)))
        session.exec(delete(CineFavorito).where(CineFavorito.user_id.in_(PRUEBA)))
        session.exec(delete(Perfil).where(Perfil.user_id.in_(PRUEBA)))
        session.merge(PeliculaOculta(pelicula_id=E))  # para comprobar el CASCADE al borrar la película
        session.flush()
        session.exec(delete(Pase).where(Pase.pelicula_id.in_(PELIS)))
        session.exec(delete(PeliculaOculta).where(PeliculaOculta.pelicula_id == S))
        session.exec(delete(Pelicula).where(Pelicula.id.in_(PELIS)))
        session.exec(delete(Cine).where(Cine.id == cine_id))
        session.commit()
        assert not session.exec(select(PeliculaOculta).where(PeliculaOculta.pelicula_id.in_(PELIS))).all(), "CASCADE"
        assert not session.exec(select(Perfil).where(Perfil.user_id.in_(PRUEBA))).all()
    print("Limpieza: datos de prueba borrados (y ON DELETE CASCADE de pelicula_oculta)")

print("TODO OK: check_admin")
