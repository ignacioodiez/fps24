"""Self-check de amigos y bloqueos (migración 0020, app/amigos.py y la visibilidad de GET /u/{usuario}) contra la BD
local. Sin red.
Uso: docker compose exec api python tests/check_amigos.py
Cliente ASGI mínimo como el de check_diario.py (no hay httpx), con usuario_actual y usuario_opcional sustituidos por
usuarios de prueba. Crea sus propios perfiles y los borra al final (con ellos, en cascada, sus amistades y bloqueos);
no crea ni borra películas ni cines."""
import asyncio
import importlib.util
import itertools
import json
import subprocess
import sys
import uuid
from datetime import timedelta
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, delete, select

from app import amigos as modulo
from app.auth import Usuario, usuario_actual, usuario_opcional
from app.database.engine import engine
from app.database.models import Amistad, Bloqueo, Cine, CineFavorito, DiarioEntrada, Pelicula, Perfil
from app.perfil import NIVELES
from app.services.tiempo import hoy_madrid
from main import app

if engine.url.host not in ("db", "localhost", "127.0.0.1"):
    sys.exit(f"Me niego: la BD no es local (host {engine.url.host!r})")

subprocess.run(["alembic", "upgrade", "head"], cwd=BACKEND, check=True)


def llamar(metodo, ruta, cuerpo=None):
    """Petición HTTP a la app por ASGI; devuelve (status, json o None, cabeceras)."""
    ruta, _, query = ruta.partition("?")
    body = json.dumps(cuerpo).encode() if cuerpo is not None else b""
    scope = {"type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1", "method": metodo, "scheme": "http",
             "path": ruta, "raw_path": ruta.encode(), "query_string": query.encode(), "root_path": "",
             "headers": [(b"content-type", b"application/json")], "client": ("test", 1), "server": ("test", 80)}
    mensajes = [{"type": "http.request", "body": body, "more_body": False}]
    respuesta = {"status": None, "body": b"", "headers": {}}

    async def receive():
        return mensajes.pop(0) if mensajes else {"type": "http.disconnect"}

    async def send(m):
        if m["type"] == "http.response.start":
            respuesta["status"] = m["status"]
            respuesta["headers"] = {k.decode().lower(): v.decode() for k, v in m.get("headers", [])}
        elif m["type"] == "http.response.body":
            respuesta["body"] += m.get("body", b"")

    asyncio.run(app(scope, receive, send))
    return respuesta["status"], json.loads(respuesta["body"]) if respuesta["body"] else None, respuesta["headers"]


def ok(esperado, resultado, que):
    codigo, cuerpo, _ = resultado
    assert codigo == esperado, (que, codigo, cuerpo)
    print(f"OK: {que} -> {codigo}")
    return cuerpo


sufijo = uuid.uuid4().hex[:6]
NOMBRES = dict(dueno=f"chk_dueno{sufijo}", amigo=f"chk_amigo{sufijo}", otro=f"chk_otro{sufijo}",
               bloq=f"chk_bloq{sufijo}", lim=f"chk_lim{sufijo}")
IDS = {k: uuid.uuid4() for k in NOMBRES}
SIN_PERFIL = uuid.uuid4()
RELLENO = [uuid.uuid4() for _ in range(modulo.MAX_PENDIENTES)]  # destinatarios para llenar el tope de pendientes
PRUEBA = [*IDS.values(), SIN_PERFIL, *RELLENO]
EMAIL = "chk_amigos@ejemplo.es"
actual = {"id": None}  # None: sin sesión
app.dependency_overrides[usuario_actual] = lambda: Usuario(id=str(actual["id"]), email=EMAIL)
app.dependency_overrides[usuario_opcional] = lambda: actual["id"] and Usuario(id=str(actual["id"]), email=EMAIL)
VISTO = []  # todas las respuestas, para buscar fugas al final


def como(quien):
    actual["id"] = IDS.get(quien, quien) if quien else None


def pedir(quien, a_quien):
    como(quien)
    r = llamar("POST", "/me/amigos/solicitudes", {"usuario": a_quien})
    VISTO.append(r[1])
    return r[:2]


def mis_amigos(quien):
    como(quien)
    datos = ok(200, llamar("GET", "/me/amigos"), f"GET /me/amigos de {quien}")
    VISTO.append(datos)
    return datos


def nombres(lista):
    return [p["usuario"] for p in lista]


def pares():
    with Session(engine) as session:
        return {(a.solicitante_id, a.destinatario_id, a.estado) for a in session.exec(
            select(Amistad).where(Amistad.solicitante_id.in_(PRUEBA) | Amistad.destinatario_id.in_(PRUEBA)))}


try:
    with Session(engine) as session:
        for k, nombre in NOMBRES.items():
            session.add(Perfil(user_id=IDS[k], usuario=nombre, bio="bio de prueba", letterboxd_usuario="chk_lbx"))
        session.add_all(Perfil(user_id=u, usuario=f"chk_r{i}_{sufijo}") for i, u in enumerate(RELLENO))
        peli = session.exec(select(Pelicula.id).order_by(Pelicula.id)).first()
        cine = session.exec(select(Cine.id).order_by(Cine.id)).first()
        assert peli and cine, "hacen falta una película y un cine en la BD local"
        session.commit()
        session.add(DiarioEntrada(user_id=IDS["dueno"], pelicula_id=peli, fecha_vista=hoy_madrid()))
        session.add(CineFavorito(user_id=IDS["dueno"], cine_id=cine))
        session.commit()
    D, A, O, B = (IDS[k] for k in ("dueno", "amigo", "otro", "bloq"))

    # --- Sin perfil propio: error claro, sin mirar a quién ---
    como(SIN_PERFIL)
    assert "nombre de usuario" in ok(422, llamar("POST", "/me/amigos/solicitudes", {"usuario": NOMBRES["dueno"]}), "sin perfil")["detail"]
    assert mis_amigos(SIN_PERFIL) == {"amigos": [], "recibidas": [], "enviadas": []}

    # --- Solicitud, aceptar; la respuesta es siempre la misma ---
    igual = (200, modulo.ENVIADA)
    assert pedir("amigo", f"  @{NOMBRES['dueno'].upper()} ") == igual  # se normaliza: sin @, sin espacios, minúsculas
    assert pares() == {(A, D, "pendiente")}
    recibidas = mis_amigos("dueno")["recibidas"]
    assert nombres(recibidas) == [NOMBRES["amigo"]] and set(recibidas[0]) == {"id", "usuario", "avatar", "creada_en"}, recibidas
    assert nombres(mis_amigos("amigo")["enviadas"]) == [NOMBRES["dueno"]]
    sol = recibidas[0]["id"]
    como("amigo")  # el solicitante no puede aceptar su propia solicitud
    ok(404, llamar("POST", f"/me/amigos/solicitudes/{sol}/aceptar"), "aceptar la mía")
    como("otro")  # ni un tercero, ni rechazarla ni cancelarla
    ok(404, llamar("POST", f"/me/amigos/solicitudes/{sol}/aceptar"), "aceptar ajena")
    ok(404, llamar("POST", f"/me/amigos/solicitudes/{sol}/rechazar"), "rechazar ajena")
    ok(204, llamar("DELETE", f"/me/amigos/solicitudes/{sol}"), "cancelar ajena (no hace nada)")
    assert pares() == {(A, D, "pendiente")}
    como("dueno")
    ok(204, llamar("POST", f"/me/amigos/solicitudes/{sol}/aceptar"), "aceptar")
    ok(404, llamar("POST", f"/me/amigos/solicitudes/{sol}/aceptar"), "aceptar dos veces")
    ok(422, llamar("POST", "/me/amigos/solicitudes/no-es-un-id/aceptar"), "id no válido")
    assert nombres(mis_amigos("dueno")["amigos"]) == [NOMBRES["amigo"]] and nombres(mis_amigos("amigo")["amigos"]) == [NOMBRES["dueno"]]
    print("OK: solicitud y aceptación (solo el destinatario; ids opacos)")

    # --- Bloqueo: dueno bloquea a bloq (antes, amigos y con solicitud) ---
    pedir("bloq", NOMBRES["dueno"])
    como("dueno")
    ok(204, llamar("POST", f"/me/amigos/solicitudes/{mis_amigos('dueno')['recibidas'][0]['id']}/aceptar"), "dueno acepta a bloq")
    ok(204, llamar("POST", "/me/bloqueos", {"usuario": f"@{NOMBRES['bloq']}"}), "bloquear")
    ok(204, llamar("POST", "/me/bloqueos", {"usuario": NOMBRES["bloq"]}), "bloquear dos veces")
    for quien in (f"nadie_{sufijo}", NOMBRES["dueno"], "x" * 300):
        ok(204, llamar("POST", "/me/bloqueos", {"usuario": quien}), f"bloquear {quien[:20]} (siempre 204)")
    assert nombres(ok(200, llamar("GET", "/me/bloqueos"), "mis bloqueos")) == [NOMBRES["bloq"]]
    assert all(B not in (s, d) for s, d, _ in pares()), "bloquear borra la amistad"
    print("OK: bloquear borra la amistad y es idempotente")

    # --- La respuesta a una solicitud es idéntica para existente, inexistente, uno mismo, bloqueado y ya amigo ---
    with Session(engine) as session:
        session.add(Bloqueo(bloqueador_id=O, bloqueado_id=IDS["lim"]))  # otro bloquea a lim: el otro sentido
        session.commit()
    antes = pares()
    casos = [("amigo", f"nadie_{sufijo}"), ("amigo", NOMBRES["amigo"]), ("amigo", NOMBRES["dueno"]),
             ("bloq", NOMBRES["dueno"]), ("dueno", NOMBRES["bloq"]), ("lim", NOMBRES["otro"]), ("amigo", "x" * 300), ("amigo", "")]
    assert all(pedir(q, a) == igual for q, a in casos), [pedir(q, a) for q, a in casos]
    assert pares() == antes, "ninguna de esas crea nada"
    assert pedir("otro", NOMBRES["dueno"]) == igual and (O, D, "pendiente") in pares()  # existente
    print("OK: misma respuesta para existente, inexistente, uno mismo, bloqueado (en los dos sentidos) y ya amigo")

    # --- Rechazar y cancelar ---
    como("dueno")
    sol = mis_amigos("dueno")["recibidas"][0]["id"]
    ok(204, llamar("POST", f"/me/amigos/solicitudes/{sol}/rechazar"), "rechazar")
    assert not mis_amigos("otro")["enviadas"] and (O, D, "pendiente") not in pares()
    pedir("otro", NOMBRES["dueno"])
    sol = mis_amigos("otro")["enviadas"][0]["id"]
    como("dueno")  # el destinatario no la cancela (para eso está rechazar)
    ok(204, llamar("DELETE", f"/me/amigos/solicitudes/{sol}"), "cancelar recibida (no hace nada)")
    assert (O, D, "pendiente") in pares()
    como("otro")
    ok(204, llamar("DELETE", f"/me/amigos/solicitudes/{sol}"), "cancelar")
    assert (O, D, "pendiente") not in pares() and not mis_amigos("dueno")["recibidas"]
    print("OK: rechazar (el destinatario) y cancelar (el solicitante)")

    # --- Solicitud cruzada: se acepta sola; quitar ---
    pedir("dueno", NOMBRES["otro"])
    assert pedir("otro", NOMBRES["dueno"]) == igual
    assert (D, O, "aceptada") in pares() and not mis_amigos("otro")["recibidas"]
    como("otro")
    ok(204, llamar("DELETE", f"/me/amigos/{NOMBRES['dueno'].upper()}"), "quitar amigo")
    ok(204, llamar("DELETE", f"/me/amigos/nadie_{sufijo}"), "quitar a quien no existe")
    assert all(O not in (s, d) for s, d, _ in pares())
    print("OK: la solicitud cruzada se acepta sola; quitar amigo")

    # --- Límites: pendientes y por día (Madrid) ---
    with Session(engine) as session:
        session.add_all(Amistad(solicitante_id=IDS["lim"], destinatario_id=u) for u in RELLENO)
        session.commit()
    como("lim")
    assert f"{modulo.MAX_PENDIENTES}" in ok(409, llamar("POST", "/me/amigos/solicitudes", {"usuario": f"nadie_{sufijo}"}), "tope de pendientes")["detail"]
    with Session(engine) as session:
        session.exec(delete(Amistad).where(Amistad.solicitante_id == IDS["lim"]))
        session.exec(Perfil.__table__.update().where(Perfil.user_id == IDS["lim"]).values(solicitudes_hoy=0, solicitudes_dia=None))
        session.commit()
    respuestas = [pedir("lim", f"nadie{i}_{sufijo}") for i in range(modulo.MAX_AL_DIA)]
    assert respuestas == [igual] * modulo.MAX_AL_DIA, respuestas
    codigo, cuerpo = pedir("lim", NOMBRES["amigo"])
    assert codigo == 429 and "por día" in cuerpo["detail"], (codigo, cuerpo)
    assert pedir("lim", f"nadie_{sufijo}")[0] == 429  # mismo error exista o no
    with Session(engine) as session:  # al día siguiente (Madrid) se puede otra vez
        session.exec(Perfil.__table__.update().where(Perfil.user_id == IDS["lim"]).values(solicitudes_dia=hoy_madrid() - timedelta(days=1)))
        session.commit()
    assert pedir("lim", NOMBRES["amigo"]) == igual
    print(f"OK: topes de {modulo.MAX_PENDIENTES} pendientes y {modulo.MAX_AL_DIA} al día")

    # --- Matriz de visibilidad de /u/{dueno}: perfil × diario × cines × quien mira ---
    como("dueno")
    inexistente = llamar("GET", f"/u/nadie_{sufijo}")
    assert inexistente[:2] == (404, {"detail": "Este perfil no existe o es privado"}) and inexistente[2]["cache-control"] == "private, no-store"
    rel_esperada = {"dueno": "yo", "amigo": "amigos", "otro": "ninguna", None: None}
    combinaciones = 0
    for perfil, diario, cines in itertools.product(NIVELES, repeat=3):
        como("dueno")
        guardado = ok(200, llamar("PUT", "/me/perfil", {"usuario": NOMBRES["dueno"], "bio": "bio de prueba", "visibilidad": perfil,
                                                        "diario_visibilidad": diario, "cines_visibilidad": cines,
                                                        "letterboxd_usuario": "chk_lbx"}), f"perfil {perfil}, diario {diario}, cines {cines}")
        # Las secciones nunca más abiertas que el perfil: se bajan a su nivel
        tope = lambda n: NIVELES[min(NIVELES.index(n), NIVELES.index(perfil))]
        assert (guardado["diario_visibilidad"], guardado["cines_visibilidad"]) == (tope(diario), tope(cines)), guardado
        diario, cines = tope(diario), tope(cines)
        for quien in ("dueno", "amigo", "otro", None, "bloq"):
            como(quien)
            codigo, cuerpo, cabeceras = r = llamar("GET", f"/u/{NOMBRES['dueno']}")
            VISTO.append(cuerpo)
            assert cabeceras["cache-control"] == "private, no-store", cabeceras
            ve = lambda n: quien == "dueno" or n == "publico" or (n == "amigos" and quien == "amigo")
            que = (perfil, diario, cines, quien)
            if quien == "bloq" or (not ve(perfil) and perfil == "privado"):
                assert r[:2] == inexistente[:2], (que, r)  # el mismo 404 que un usuario inexistente
                continue
            assert codigo == 200 and cuerpo["relacion"] == rel_esperada[quien], (que, cuerpo)
            if not ve(perfil):  # "amigos" visto por quien no lo es: tarjeta mínima
                assert cuerpo["restringido"] is True and cuerpo["usuario"] == NOMBRES["dueno"] and cuerpo["avatar"], (que, cuerpo)
                assert all(cuerpo[k] in (None, False) for k in ("bio", "letterboxd_usuario", "diario", "cines", "cifras", "diario_publico")), (que, cuerpo)
                continue
            assert cuerpo["restringido"] is False and cuerpo["bio"] == "bio de prueba" and cuerpo["letterboxd_usuario"] == "chk_lbx", (que, cuerpo)
            assert (cuerpo["diario"] is not None, cuerpo["cifras"] is not None, cuerpo["diario_publico"]) == (ve(diario),) * 3, (que, cuerpo)
            assert (cuerpo["cines"] is not None) == ve(cines), (que, cuerpo)
            assert not ve(diario) or cuerpo["diario"]["total"] == 1
            assert not ve(cines) or len(cuerpo["cines"]) == 1
        combinaciones += 1
    print(f"OK: matriz de visibilidad ({combinaciones} combinaciones × dueño, amigo, no amigo, anónimo y bloqueado)")

    # Relación vista desde el otro lado, y la de quien ha bloqueado
    como("dueno")
    ok(200, llamar("PUT", "/me/perfil", {"usuario": NOMBRES["dueno"], "visibilidad": "publico"}), "dueno público")
    pedir("otro", NOMBRES["dueno"])
    como("otro")
    assert llamar("GET", f"/u/{NOMBRES['dueno']}")[1]["relacion"] == "enviada"
    with Session(engine) as session:
        session.exec(Perfil.__table__.update().where(Perfil.user_id == O).values(visibilidad="publico"))
        session.commit()
    como("dueno")
    assert llamar("GET", f"/u/{NOMBRES['otro']}")[1]["relacion"] == "recibida"
    ok(204, llamar("POST", "/me/bloqueos", {"usuario": NOMBRES["otro"]}), "dueno bloquea a otro")
    assert llamar("GET", f"/u/{NOMBRES['otro']}")[1]["relacion"] == "bloqueado"  # quien bloquea sí lo ve, y lo sabe
    como("otro")
    assert llamar("GET", f"/u/{NOMBRES['dueno']}")[:2] == inexistente[:2]  # el bloqueado, el 404 neutro
    assert all(O not in (s, d) for s, d, _ in pares())  # y la solicitud ha desaparecido
    como("dueno")
    ok(204, llamar("DELETE", f"/me/bloqueos/{NOMBRES['otro']}"), "desbloquear")
    assert nombres(ok(200, llamar("GET", "/me/bloqueos"), "bloqueos")) == [NOMBRES["bloq"]]
    como("otro")
    assert llamar("GET", f"/u/{NOMBRES['dueno']}")[0] == 200
    print("OK: relación enviada/recibida/bloqueado; desbloquear")

    # --- Nada interno en ninguna respuesta ---
    texto = json.dumps(VISTO, default=str)
    for prohibido in (*(str(u) for u in PRUEBA), EMAIL, "user_id", "email", "solicitante", "destinatario", "bloqueador"):
        assert prohibido not in texto, prohibido
    print("OK: ni user_id, ni email, ni ids internos en las respuestas")

    # --- La tabla: un único par sin importar el orden, no a uno mismo, RLS ---
    assert (A, D, "aceptada") in pares()
    for valores, restriccion in [(dict(solicitante_id=D, destinatario_id=A), "uq_amistad_par"),
                                 (dict(solicitante_id=A, destinatario_id=A), "ck_amistad_distintos"),
                                 (dict(solicitante_id=A, destinatario_id=O, estado="rechazada"), "ck_amistad_estado")]:
        with Session(engine) as session:
            session.add(Amistad(**valores))
            try:
                session.commit()
                raise AssertionError(f"la BD debería rechazar {valores}")
            except IntegrityError as e:
                assert restriccion in str(e.orig), e
    print("OK: un único par por usuarios, no a uno mismo, estados válidos")

    spec = importlib.util.spec_from_file_location("m0020", BACKEND / "migrations/versions/0020_amigos.py")
    m0020 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m0020)
    with engine.connect() as conn:
        for tabla in ("amistad", "bloqueo"):
            assert conn.execute(text(f"SELECT relrowsecurity FROM pg_class WHERE oid = 'public.{tabla}'::regclass")).scalar(), tabla
        try:
            for rol in ("anon", "authenticated"):
                if not conn.execute(text("SELECT 1 FROM pg_roles WHERE rolname = :r"), {"r": rol}).scalar():
                    conn.execute(text(f"CREATE ROLE {rol} NOLOGIN"))
            conn.execute(text("GRANT ALL ON public.amistad, public.bloqueo TO anon, authenticated"))
            conn.execute(text(m0020.SQL_RLS))
            for rol, tabla in itertools.product(("anon", "authenticated"), ("amistad", "bloqueo")):
                assert not conn.execute(text(f"SELECT has_table_privilege(:r, 'public.{tabla}', 'SELECT')"), {"r": rol}).scalar(), (rol, tabla)
        finally:
            conn.rollback()
    print("OK: amistad y bloqueo con RLS y sin permisos para anon/authenticated")

    # --- Borrar la cuenta (el perfil) borra en cascada sus amistades, solicitudes y bloqueos ---
    with Session(engine) as session:
        assert session.exec(select(Amistad).where((Amistad.solicitante_id == A) | (Amistad.destinatario_id == A))).first()
        assert session.get(Bloqueo, (D, B))
        session.exec(delete(Perfil).where(Perfil.user_id.in_([A, B])))
        session.commit()
        assert not session.exec(select(Amistad).where(Amistad.solicitante_id.in_([A, B]) | Amistad.destinatario_id.in_([A, B]))).first()
        assert not session.exec(select(Bloqueo).where(Bloqueo.bloqueador_id.in_([A, B]) | Bloqueo.bloqueado_id.in_([A, B]))).first()
    print("OK: borrado en cascada con la cuenta")
finally:
    app.dependency_overrides.clear()
    with Session(engine) as session:
        session.exec(delete(DiarioEntrada).where(DiarioEntrada.user_id.in_(PRUEBA)))
        session.exec(delete(CineFavorito).where(CineFavorito.user_id.in_(PRUEBA)))
        borrados = session.exec(delete(Perfil).where(Perfil.user_id.in_(PRUEBA))).rowcount  # y en cascada amistad y bloqueo
        session.commit()
        assert not session.exec(select(Amistad).where(Amistad.solicitante_id.in_(PRUEBA) | Amistad.destinatario_id.in_(PRUEBA))).first()
    print(f"Limpieza: {borrados} perfiles de prueba borrados")

print("TODO OK: check_amigos")
