"""Self-check del perfil (migración 0011 y endpoints de app/perfil.py) contra la BD local. Sin red.
Uso: docker compose exec api python tests/check_perfil.py
Llama a la app por ASGI con el cliente mínimo de check_diario.py (TestClient necesita httpx, que no está instalado),
con usuario_actual sustituido por usuarios de prueba. Borra al final todos los perfiles y entradas de diario que crea."""
import asyncio
import importlib.util
import json
import subprocess
import sys
import threading
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, delete, select

from app import perfil as modulo
from app.auth import Usuario, usuario_actual
from app.database.engine import engine
from app.services.tiempo import hoy_madrid
from app.database.models import Cine, CineFavorito, DiarioEntrada, Pelicula, Perfil
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


A, B, C, D = (uuid.uuid4() for _ in range(4))
PRUEBA = [A, B, C, D]
PELIS = []  # ids de las películas de prueba, para borrarlas al final
sufijo = uuid.uuid4().hex[:6]
NOMBRE_A, NOMBRE_B = f"chk.ana_{sufijo}", f"chk_bea{sufijo}"
actual = {"id": A}
app.dependency_overrides[usuario_actual] = lambda: Usuario(id=str(actual["id"]), email="a@ejemplo.es")


def como(usuario):
    actual["id"] = usuario


# --- Reglas del nombre (sin BD) ---
validar = modulo.validar_usuario
for valido in ("ana", "ana.diez", "a_b.c", "cine_fan", "x" * 20, "007"):
    assert validar(valido) == (valido, None), (valido, validar(valido))
assert validar("  Ana.Diez ") == ("ana.diez", None)  # se guarda en minúsculas
for invalido in ("ab", "x" * 21, "ana diez", "añil", "ana-diez", "ana@x", ".ana", "ana.", "_ana", "ana_", "an..a", "", None):
    assert validar(invalido)[1], invalido
for reservado in ("admin", "Administrador", "fps24", "api", "perfil", "cines", "pelicula", "diario", "login",
                  "soporte", "privacidad", "null", "undefined"):
    assert validar(reservado)[1] == "Ese nombre de usuario está reservado", reservado
assert all(validar(corto)[1] for corto in ("me", "u"))  # reservados, pero ya los rechaza la longitud
print("OK: reglas del nombre y reservados")

try:
    # --- Sin perfil ---
    assert ok(200, llamar("GET", "/me/perfil"), "sin perfil")["usuario"] is None

    # --- Crear, y errores claros ---
    for nombre, codigo, detalle in [("ab", 422, "entre 3 y 20"), ("admin", 422, "reservado"), (".ana", 422, "empezar"),
                                    ("an..a", 422, "dos puntos")]:
        assert detalle in ok(codigo, llamar("PUT", "/me/perfil", {"usuario": nombre}), f"nombre {nombre!r}")["detail"]
    assert "160" in ok(422, llamar("PUT", "/me/perfil", {"usuario": NOMBRE_A, "bio": "x" * 161}), "bio larga")["detail"]
    ok(422, llamar("PUT", "/me/perfil", {"usuario": NOMBRE_A, "visibilidad": "amigos"}), "visibilidad desconocida")
    creado = ok(200, llamar("PUT", "/me/perfil", {"usuario": NOMBRE_A.upper(), "bio": "  Cine de barrio  "}), "crear")
    assert creado["usuario"] == NOMBRE_A and creado["bio"] == "Cine de barrio" and creado["visibilidad"] == "privado"
    assert ok(200, llamar("GET", "/me/perfil"), "leer el mío")["usuario"] == NOMBRE_A

    # --- Unicidad sin mayúsculas, y otro usuario no puede tocar mi perfil ---
    como(B)
    assert ok(409, llamar("PUT", "/me/perfil", {"usuario": NOMBRE_A.upper()}), "nombre de A, en mayúsculas")["detail"] == "Ese nombre de usuario ya está en uso"
    assert ok(200, llamar("GET", f"/usuarios/disponible?u={NOMBRE_A.upper()}"), "disponible (ocupado)") == {
        "disponible": False, "motivo": "Ese nombre de usuario ya está en uso"}
    assert ok(200, llamar("GET", "/usuarios/disponible?u=admin"), "disponible (reservado)")["disponible"] is False
    assert ok(200, llamar("GET", f"/usuarios/disponible?u={NOMBRE_B}"), "disponible (libre)") == {"disponible": True, "motivo": None}
    ok(200, llamar("PUT", "/me/perfil", {"usuario": NOMBRE_B, "visibilidad": "publico"}), "B crea el suyo")
    with Session(engine) as session:
        a = session.get(Perfil, A)
        assert (a.usuario, a.bio, a.visibilidad) == (NOMBRE_A, "Cine de barrio", "privado"), a  # A sigue igual
        assert session.get(Perfil, B).usuario == NOMBRE_B
    como(A)
    assert ok(200, llamar("GET", f"/usuarios/disponible?u={NOMBRE_A}"), "disponible (el mío)")["disponible"] is True
    print("OK: B no puede quedarse el nombre de A ni cambiar su perfil")

    # --- Público: privado e inexistente responden igual; público solo usuario y bio ---
    privado = llamar("GET", f"/u/{NOMBRE_A}")
    for ruta in (f"/u/nadie_{sufijo}", "/u/admin", "/u/..", "/u/" + "x" * 300):
        assert llamar("GET", ruta) == privado, (ruta, llamar("GET", ruta), privado)
    assert privado == (404, {"detail": "Este perfil no existe o es privado"}), privado
    print("OK: privado e inexistente, mismo 404")
    ok(200, llamar("PUT", "/me/perfil", {"usuario": NOMBRE_A, "bio": "Cine de barrio", "visibilidad": "publico"}), "hacerlo público")
    publico = ok(200, llamar("GET", f"/u/{NOMBRE_A.upper()}"), "público, sin mayúsculas")
    # ni user_id, ni email, ni fechas; sin diario ni cines mientras no se activen
    color = modulo.color_avatar(Perfil(usuario=NOMBRE_A))
    assert publico == {"usuario": NOMBRE_A, "bio": "Cine de barrio", "diario_publico": False, "diario": None, "cines": None, "cifras": None,
                       "letterboxd_usuario": None, "avatar": {"tipo": "iniciales", "color": color,
                                                              "fondo": modulo.PALETA_AVATAR[color], "poster_url": None}}, publico
    ok(200, llamar("PUT", "/me/perfil", {"usuario": NOMBRE_A, "bio": "Cine de barrio"}), "PUT sin visibilidad")
    assert llamar("GET", f"/u/{NOMBRE_A}") == privado  # PUT sin visibilidad vuelve a privado
    app.dependency_overrides.clear()  # sin sesión: el público sigue respondiendo; los demás no
    assert llamar("GET", f"/u/{NOMBRE_B}")[0] == 200
    for metodo, ruta in [("GET", "/me/perfil"), ("PUT", "/me/perfil"), ("GET", "/usuarios/disponible?u=ana")]:
        assert llamar(metodo, ruta, {"usuario": "ana"} if metodo == "PUT" else None)[0] in (401, 503), ruta
    app.dependency_overrides[usuario_actual] = lambda: Usuario(id=str(actual["id"]), email="a@ejemplo.es")
    print("OK: sin sesión, solo /u/{usuario}")

    # --- Diario en el perfil público: solo si el perfil es público Y diario_publico ---
    with Session(engine) as session:
        peli = session.exec(select(Pelicula).order_by(Pelicula.id)).first()
        cine = session.exec(select(Cine).order_by(Cine.id)).first()
        hoy = date(2026, 1, 31)
        # 31 entradas de A (una con cine, nota y nota de texto) y una de B, que no debe colarse
        for i in range(31):
            session.add(DiarioEntrada(user_id=A, pelicula_id=peli.id, fecha_vista=hoy - timedelta(days=i),
                                      **(dict(cine_id=cine.id, nota=8, comentario="Muy buena") if i == 0 else {})))
        session.add(DiarioEntrada(user_id=B, pelicula_id=peli.id, fecha_vista=hoy))
        session.commit()
        ids_a = set(session.exec(select(DiarioEntrada.id).where(DiarioEntrada.user_id == A)).all())
        peli_id, cine_json = peli.id, {"slug": cine.slug, "nombre": cine.nombre}

    def poner(visibilidad, diario):
        mio = ok(200, llamar("PUT", "/me/perfil", {"usuario": NOMBRE_A, "bio": "Cine de barrio", "visibilidad": visibilidad,
                                                   "diario_publico": diario}), f"{visibilidad}, diario_publico={diario}")
        assert (mio["visibilidad"], mio["diario_publico"]) == (visibilidad, diario), mio
        assert ok(200, llamar("GET", "/me/perfil"), "GET /me/perfil")["diario_publico"] is diario

    poner("privado", True)
    assert llamar("GET", f"/u/{NOMBRE_A}") == privado  # privado: 404 aunque diario_publico
    poner("publico", False)
    assert ok(200, llamar("GET", f"/u/{NOMBRE_A}"), "público sin diario")["diario"] is None
    poner("publico", True)
    pagina1 = ok(200, llamar("GET", f"/u/{NOMBRE_A}"), "público con diario")
    diario = pagina1["diario"]
    assert pagina1["diario_publico"] is True and diario["total"] == 31 and diario["por_pagina"] == modulo.POR_PAGINA == 30
    assert diario["pagina"] == 1 and len(diario["entradas"]) == 30
    primera = diario["entradas"][0]
    assert set(primera) == {"pelicula", "cine", "fecha_vista", "nota", "comentario"}, primera  # ni id, ni user_id, ni pase
    assert (primera["fecha_vista"], primera["nota"], primera["comentario"]) == (str(hoy), 8, "Muy buena"), primera
    assert primera["cine"] == cine_json and primera["pelicula"]["id"] == peli_id
    assert diario["entradas"][1]["cine"] is None
    fechas = [e["fecha_vista"] for e in diario["entradas"]]
    assert fechas == sorted(fechas, reverse=True), fechas  # más reciente primero
    texto = json.dumps(pagina1)
    for prohibido in (str(A), str(B), "a@ejemplo.es", "user_id", "email", "creado_en", *(f'"id": {i},' for i in ids_a)):
        assert prohibido not in texto, prohibido
    pagina2 = ok(200, llamar("GET", f"/u/{NOMBRE_A}?pagina=2"), "página 2")["diario"]
    assert pagina2["pagina"] == 2 and len(pagina2["entradas"]) == 1 and pagina2["entradas"][0]["fecha_vista"] == str(hoy - timedelta(days=30))
    assert ok(200, llamar("GET", f"/u/{NOMBRE_A}?pagina=3"), "página 3")["diario"]["entradas"] == []
    # pagina no válida: 422 igual para cualquier nombre, antes de buscar el perfil (no distingue privado de inexistente)
    assert llamar("GET", f"/u/{NOMBRE_A}?pagina=0")[0] == llamar("GET", f"/u/nadie_{sufijo}?pagina=0")[0] == 422
    # Póster e id de la película en cada entrada (para enlazar a /pelicula/<id>), sin nada más de la película interna
    assert {"id", "titulo", "poster_url"} <= set(primera["pelicula"]), primera["pelicula"]
    # Cifras: total y este año (Madrid), en /u y en mi /diario; una entrada de hoy cuenta, una del 31-dic anterior no
    enero = date(hoy_madrid().year, 1, 1)
    with Session(engine) as session:
        session.add_all([DiarioEntrada(user_id=A, pelicula_id=peli_id, fecha_vista=hoy_madrid()),
                         DiarioEntrada(user_id=A, pelicula_id=peli_id, fecha_vista=enero - timedelta(days=1))])
        session.commit()
    fechas_a = [hoy - timedelta(days=i) for i in range(31)] + [hoy_madrid(), enero - timedelta(days=1)]
    esperadas = {"entradas": len(fechas_a), "este_anio": sum(f >= enero for f in fechas_a)}
    assert ok(200, llamar("GET", f"/u/{NOMBRE_A}"), "cifras")["cifras"] == esperadas, esperadas
    mi_diario = ok(200, llamar("GET", "/diario?limite=1"), "mi diario con cifras")
    assert (mi_diario["total"], mi_diario["este_anio"]) == (esperadas["entradas"], esperadas["este_anio"]), mi_diario
    with Session(engine) as session:
        session.exec(delete(DiarioEntrada).where(DiarioEntrada.user_id == A, DiarioEntrada.fecha_vista.in_([hoy_madrid(), enero - timedelta(days=1)])))
        session.commit()
    print("OK: cifras (total y este año en Madrid) y póster/id en las entradas")
    # Al momento: apagarlo, o pasar a privado, lo oculta en la siguiente petición
    poner("publico", False)
    assert llamar("GET", f"/u/{NOMBRE_A}")[1]["diario"] is None
    poner("publico", True)
    poner("privado", True)
    assert llamar("GET", f"/u/{NOMBRE_A}") == privado
    assert llamar("GET", f"/u/{NOMBRE_A}?pagina=2") == privado
    ok(200, llamar("PUT", "/me/perfil", {"usuario": NOMBRE_A, "visibilidad": "publico"}), "PUT sin diario_publico")
    assert llamar("GET", f"/u/{NOMBRE_A}")[1]["diario"] is None  # sin el campo, se apaga
    print("OK: diario en el perfil público (oculto si privado o apagado, paginado, sin campos internos, al momento)")

    # --- Avatar, Letterboxd y cines favoritos en el perfil público ---
    with Session(engine) as session:
        con_poster = Pelicula(titulo=f"chk_con_poster_{sufijo}", poster_url="https://image.tmdb.org/t/p/w500/chk.jpg")
        sin_poster = Pelicula(titulo=f"chk_sin_poster_{sufijo}")
        borrable = Pelicula(titulo=f"chk_borrable_{sufijo}", poster_url="https://image.tmdb.org/t/p/w500/chk2.jpg")
        session.add_all([con_poster, sin_poster, borrable])
        session.commit()
        PELIS.extend([con_poster.id, sin_poster.id, borrable.id])
        con_poster_id, sin_poster_id, borrable_id = con_poster.id, sin_poster.id, borrable.id
        cines = session.exec(select(Cine).order_by(Cine.id).limit(3)).all()
        assert len(cines) == 3, "hacen falta 3 cines en la BD local"
        for i, (uid, c) in enumerate([(A, cines[1]), (A, cines[0]), (B, cines[2])]):  # A: primero el 1, luego el 0
            session.add(CineFavorito(user_id=uid, cine_id=c.id, creado_en=datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(minutes=i)))
        session.commit()
        cines_a = [{"slug": c.slug, "nombre": c.nombre, "zona": c.zona} for c in (cines[1], cines[0])]
        slug_de_b = cines[2].slug

    def guardar_a(codigo=200, visibilidad="publico", **extra):
        return ok(codigo, llamar("PUT", "/me/perfil", {"usuario": NOMBRE_A, "visibilidad": visibilidad, **extra}), f"PUT {extra}")

    # Letterboxd: el usuario tal cual (con sus mayúsculas), o sacado de la URL de su perfil
    lb = modulo.validar_letterboxd
    for entrada, esperado in [("Ana_Diez", "Ana_Diez"), ("  @cine_fan ", "cine_fan"), ("https://letterboxd.com/Ana_Diez/", "Ana_Diez"),
                              ("letterboxd.com/ana", "ana"), ("http://www.letterboxd.com/ana/films/diary/", "ana"),
                              ("HTTPS://LETTERBOXD.COM/ana?x=1", "ana"), ("ab", "ab"), ("x" * 20, "x" * 20),
                              ("", None), ("   ", None), (None, None)]:
        assert lb(entrada) == (esperado, None), (entrada, lb(entrada))
    for malo in ("a", "x" * 21, "ana diez", "ana.diez", "añil", "ana-diez", "<script>", "https://letterboxd.com/film/dune/",
                 "https://letterboxd.com/", "https://boxd.it/abc", "https://otra.com/ana", "letterboxd.com.mal.es/ana"):
        assert lb(malo) == (None, modulo.ERROR_LETTERBOXD), (malo, lb(malo))
    assert "Letterboxd" in guardar_a(422, letterboxd_usuario="ana diez")["detail"]
    assert guardar_a(letterboxd_usuario="https://letterboxd.com/Ana_Diez/")["letterboxd_usuario"] == "Ana_Diez"
    print("OK: Letterboxd (usuario o URL, se guarda tal cual)")

    # Paleta: 6-8 colores, todos legibles con texto blanco (contraste WCAG >= 4.5)
    def luminancia(hexa):
        c = [int(hexa[i:i + 2], 16) / 255 for i in (1, 3, 5)]
        c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
        return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
    assert 6 <= len(modulo.PALETA_AVATAR) <= 8
    for nombre, hexa in modulo.PALETA_AVATAR.items():
        assert 1.05 / (luminancia(hexa) + 0.05) >= 4.5, (nombre, hexa)
    assert modulo.color_avatar(Perfil(usuario="Ana")) == modulo.color_avatar(Perfil(usuario="ana"))  # determinista
    assert "paleta" in guardar_a(422, avatar_color="#ff0000")["detail"]
    assert "paleta" in guardar_a(422, avatar_color="dorado")["detail"]
    mio = guardar_a(avatar_color="azul")
    assert mio["avatar"] == {"tipo": "iniciales", "color": "azul", "fondo": modulo.PALETA_AVATAR["azul"], "poster_url": None}
    assert ok(200, llamar("GET", "/me/perfil"), "GET /me/perfil")["paleta_avatar"] == modulo.PALETA_AVATAR
    print("OK: paleta (contraste, determinista y solo sus colores)")

    # Avatar de película: solo de nuestra BD y con póster
    for extra in (dict(), dict(avatar_pelicula_id=sin_poster_id), dict(avatar_pelicula_id=2_000_000_000)):
        assert "póster" in guardar_a(422, avatar_tipo="pelicula", **extra)["detail"], extra
    ok(422, llamar("PUT", "/me/perfil", {"usuario": NOMBRE_A, "avatar_tipo": "foto"}), "avatar_tipo desconocido")
    mio = guardar_a(avatar_tipo="pelicula", avatar_pelicula_id=con_poster_id, avatar_color="verde")
    assert mio["avatar_pelicula_id"] == con_poster_id and mio["avatar"]["tipo"] == "pelicula"
    assert llamar("GET", f"/u/{NOMBRE_A}")[1]["avatar"] == {"tipo": "pelicula", "color": "verde", "fondo": modulo.PALETA_AVATAR["verde"],
                                                           "poster_url": "https://image.tmdb.org/t/p/w500/chk.jpg"}
    # con iniciales no se guarda la película
    assert guardar_a(avatar_tipo="iniciales", avatar_pelicula_id=con_poster_id)["avatar_pelicula_id"] is None
    # si la película se borra (ON DELETE SET NULL), vuelve a las iniciales
    guardar_a(avatar_tipo="pelicula", avatar_pelicula_id=borrable_id)
    with Session(engine) as session:
        session.exec(delete(Pelicula).where(Pelicula.id == borrable_id))
        session.commit()
    mio = ok(200, llamar("GET", "/me/perfil"), "tras borrar la película")
    assert mio["avatar_pelicula_id"] is None and mio["avatar"]["tipo"] == "iniciales", mio
    print("OK: avatar de película (válida, sin póster, inexistente, borrada)")

    # Cines: solo con el interruptor Y el perfil público; los de A, en su orden, sin los de B
    guardar_a(cines_publicos=False)
    assert llamar("GET", f"/u/{NOMBRE_A}")[1]["cines"] is None
    guardar_a(cines_publicos=True, letterboxd_usuario="Ana_Diez", avatar_tipo="pelicula", avatar_pelicula_id=con_poster_id)
    completo = ok(200, llamar("GET", f"/u/{NOMBRE_A}"), "público con cines")
    assert completo["cines"] == cines_a, completo["cines"]
    assert guardar_a(visibilidad="privado", cines_publicos=True)["cines_publicos"] is True
    assert llamar("GET", f"/u/{NOMBRE_A}") == privado  # privado: 404 aunque cines_publicos
    guardar_a(visibilidad="publico")
    assert llamar("GET", f"/u/{NOMBRE_A}")[1]["cines"] is None  # PUT sin el campo: se apaga
    # Nada interno en el público
    assert set(completo) == {"usuario", "bio", "avatar", "letterboxd_usuario", "diario_publico", "diario", "cines", "cifras"}, completo
    assert completo["cifras"] is None and set(completo["cines"][0]) == {"slug", "nombre", "zona"}  # diario apagado: sin cifras
    assert set(completo["avatar"]) == {"tipo", "color", "fondo", "poster_url"}
    texto = json.dumps(completo)
    for prohibido in (str(A), str(B), "a@ejemplo.es", "user_id", "email", "creado_en", "cines_publicos", "avatar_pelicula_id",
                      "paleta", "visibilidad", f'"id": {con_poster_id}', f'"{slug_de_b}"'):
        assert prohibido not in texto, prohibido
    print("OK: cines en el perfil público (solo con interruptor y perfil público) y sin campos internos")
    guardar_a(visibilidad="privado")

    # --- Cambiar de nombre libera el anterior ---
    ok(200, llamar("PUT", "/me/perfil", {"usuario": NOMBRE_A + "x"}), "cambiar de nombre")
    como(B)
    assert ok(200, llamar("GET", f"/usuarios/disponible?u={NOMBRE_A}"), "el antiguo queda libre")["disponible"] is True
    como(A)
    ok(200, llamar("PUT", "/me/perfil", {"usuario": NOMBRE_A}), "volver al nombre")

    # --- Carreras: dos usuarios a por el mismo nombre, y el mismo usuario creando dos veces a la vez ---
    def a_la_vez(peticiones):
        barrera, resultados = threading.Barrier(len(peticiones)), []

        def una(uid, nombre):
            with Session(engine) as session:
                barrera.wait()
                try:
                    modulo.guardar_mi_perfil(modulo.PerfilGuardar(usuario=nombre), Usuario(id=str(uid), email=None), session)
                    resultados.append(200)
                except HTTPException as e:
                    resultados.append(e.status_code)

        hilos = [threading.Thread(target=una, args=p) for p in peticiones]
        for h in hilos:
            h.start()
        for h in hilos:
            h.join()
        return sorted(resultados)

    disputado = f"chk_carrera{sufijo}"
    for _ in range(5):
        assert a_la_vez([(C, disputado), (D, disputado.upper())]) == [200, 409]
        with Session(engine) as session:
            session.exec(delete(Perfil).where(Perfil.user_id.in_([C, D])))
            session.commit()
    assert a_la_vez([(C, disputado), (C, disputado)]) == [200, 200]
    with Session(engine) as session:
        assert len(session.exec(select(Perfil).where(Perfil.user_id == C)).all()) == 1
    print("OK: carreras (un 200 y un 409; el mismo usuario dos veces, un solo perfil)")

    # --- Límite de /usuarios/disponible ---
    como(D)
    codigos = [llamar("GET", "/usuarios/disponible?u=algo_libre")[0] for _ in range(modulo.LIMITE_DISPONIBLE + 1)]
    assert codigos[:-1] == [200] * modulo.LIMITE_DISPONIBLE and codigos[-1] == 429, codigos
    print(f"OK: /usuarios/disponible, 429 tras {modulo.LIMITE_DISPONIBLE} consultas por minuto")

    # --- La tabla: UNIQUE en minúsculas, CHECK y RLS/REVOKE ---
    for valores, restriccion in [(dict(usuario=NOMBRE_A.upper()), "uq_perfil_usuario"),
                                 (dict(usuario=f"chk_bio{sufijo}", bio="x" * 161), "ck_perfil_bio"),
                                 (dict(usuario=f"chk_vis{sufijo}", visibilidad="amigos"), "ck_perfil_visibilidad"),
                                 (dict(usuario=f"chk_ava{sufijo}", avatar_tipo="foto"), "ck_perfil_avatar_tipo"),
                                 (dict(usuario=f"chk_lbx{sufijo}", letterboxd_usuario="ana diez"), "ck_perfil_letterboxd")]:
        with Session(engine) as session:
            session.add(Perfil(user_id=D, **valores))
            try:
                session.commit()
                raise AssertionError(f"la BD debería rechazar {valores}")
            except IntegrityError as e:
                assert restriccion in str(e.orig), e
    with Session(engine) as session:
        session.add(Perfil(user_id=D, usuario=f"chk_def{sufijo}"))
        session.commit()
        assert session.get(Perfil, D).visibilidad == "privado"  # privado por defecto también en la BD
    print("OK: UNIQUE sin mayúsculas, CHECK y privado por defecto en la BD")

    spec = importlib.util.spec_from_file_location("m0011", BACKEND / "migrations/versions/0011_perfil.py")
    m0011 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m0011)
    with engine.connect() as conn:
        assert conn.execute(text("SELECT relrowsecurity FROM pg_class WHERE oid = 'public.perfil'::regclass")).scalar()
        try:
            for rol in ("anon", "authenticated"):
                if not conn.execute(text("SELECT 1 FROM pg_roles WHERE rolname = :r"), {"r": rol}).scalar():
                    conn.execute(text(f"CREATE ROLE {rol} NOLOGIN"))
            conn.execute(text("GRANT ALL ON public.perfil TO anon, authenticated"))
            conn.execute(text(m0011.SQL_RLS))
            for rol in ("anon", "authenticated"):
                assert not conn.execute(text("SELECT has_table_privilege(:r, 'public.perfil', 'SELECT')"), {"r": rol}).scalar(), rol
            print("OK: perfil con RLS y sin permisos para anon/authenticated")
        finally:
            conn.rollback()
finally:
    app.dependency_overrides.clear()
    with Session(engine) as session:
        session.exec(delete(DiarioEntrada).where(DiarioEntrada.user_id.in_(PRUEBA)))
        session.exec(delete(CineFavorito).where(CineFavorito.user_id.in_(PRUEBA)))
        session.exec(delete(Pelicula).where(Pelicula.id.in_(PELIS)))
        borrados = session.exec(delete(Perfil).where(Perfil.user_id.in_(PRUEBA))).rowcount
        session.commit()
        assert not session.exec(select(Perfil).where(Perfil.user_id.in_(PRUEBA))).all()
    print(f"Limpieza: {borrados} perfiles de prueba borrados")

print("TODO OK: check_perfil")
