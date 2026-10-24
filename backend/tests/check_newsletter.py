"""Self-check de la newsletter (app/newsletter, migración 0015 y lo suyo en app/admin.py) contra la BD local.
Uso: docker compose exec api python tests/check_newsletter.py
Nunca envía correos: correo.cliente se sustituye por uno simulado que los apunta y requests.post queda bloqueado.
Llama a la app por ASGI (TestClient necesita httpx, que no está instalado). Crea suscriptores chk-nl-*, una semana
de 2031 en newsletter_envio y un cine con películas y pases en enero de 2031 (ventana de 7 días), y lo borra todo al
final."""
import asyncio
import json
import os
import re
import subprocess
import sys
import uuid
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

import requests
from sqlalchemy import text
from sqlmodel import Session, delete, select, update

from app import admin
from app.auth import Usuario
from app.database.engine import engine
from app.database.models import Cine, NewsletterEnvio, Pase, Pelicula, PeliculaOculta, Suscriptor
from app.newsletter import contenido, correo, enviar, plantilla, rutas
from app.services import destacadas as d
from main import app

if engine.url.host not in ("db", "localhost", "127.0.0.1"):
    sys.exit(f"Me niego: la BD no es local (host {engine.url.host!r})")

subprocess.run(["alembic", "upgrade", "head"], cwd=BACKEND, check=True)


# --- Nada sale a la red: cliente de correo simulado y requests.post bloqueado ---
class CorreoFalso:
    def __init__(self):
        self.enviados, self.lotes, self.fallar = [], [], False

    def enviar(self, c):
        if self.fallar:
            raise RuntimeError("Resend caído (simulado)")
        self.enviados.append(c)
        return {"id": "falso"}

    def enviar_lote(self, cs):
        if self.fallar:
            raise RuntimeError("Resend caído (simulado)")
        self.lotes.append(cs)
        self.enviados += cs
        return {"data": [{"id": "falso"} for _ in cs]}


def _prohibido(*a, **k):
    raise AssertionError("los tests no pueden llamar a la red")


falso = CorreoFalso()
correo.cliente = lambda: falso
requests.post = _prohibido
os.environ["RESEND_API_KEY"] = ""
os.environ["API_URL_PUBLICA"] = "https://api.ejemplo.test"
correo.PAUSA = 0


def llamar(metodo, ruta, cuerpo=None, ip="10.0.0.1"):
    """Petición HTTP a la app por ASGI; devuelve (status, cuerpo en bytes, cabeceras)."""
    ruta, _, query = ruta.partition("?")
    body = json.dumps(cuerpo).encode() if cuerpo is not None else b""
    scope = {"type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1", "method": metodo, "scheme": "http",
             "path": ruta, "raw_path": ruta.encode(), "query_string": query.encode(), "root_path": "",
             "headers": [(b"content-type", b"application/json"), (b"x-forwarded-for", ip.encode())],
             "client": ("test", 1), "server": ("test", 80)}
    mensajes = [{"type": "http.request", "body": body, "more_body": False}]
    respuesta = {"status": None, "body": b"", "headers": {}}

    async def receive():
        return mensajes.pop(0) if mensajes else {"type": "http.disconnect"}

    async def send(m):
        if m["type"] == "http.response.start":
            respuesta["status"] = m["status"]
            respuesta["headers"] = {k.decode(): v.decode() for k, v in m.get("headers", [])}
        elif m["type"] == "http.response.body":
            respuesta["body"] += m.get("body", b"")

    asyncio.run(app(scope, receive, send))
    return respuesta["status"], respuesta["body"], respuesta["headers"]


def suscribir(email, ip="10.0.0.1", web=""):
    codigo, cuerpo, _ = llamar("POST", "/newsletter/suscribir", {"email": email, "web": web}, ip)
    return codigo, cuerpo


def fila(email):
    with Session(engine) as session:
        return session.exec(select(Suscriptor).where(Suscriptor.email == email.lower())).first()


def cambiar(email, **valores):
    with Session(engine) as session:
        session.exec(update(Suscriptor).where(Suscriptor.email == email.lower()).values(**valores))
        session.commit()


def token_de(c):
    return re.search(r"token=([\w-]+)", c["text"]).group(1)


sufijo = uuid.uuid4().hex[:6]
mail = lambda nombre: f"chk-nl-{sufijo}-{nombre}@ejemplo.test"
SEMANA_TEST = "2031-W02"  # lunes 6 de enero de 2031
LUNES_16 = datetime(2031, 1, 6, 16, 5)
pelis_ventana, cine_ventana = [], None

try:
    # --- Ventana: el día de envío y los 6 siguientes, por nota, sin ocultas; las páginas siguen en semana natural ---
    dia = lambda n: date(2031, 1, 6) + timedelta(days=n)  # dia(0) = lunes 6/1/2031
    with Session(engine) as session:
        cine = Cine(slug=f"chk-nl-{sufijo}", nombre=f"Cine newsletter {sufijo}", tipo=d.TIPO_CINE_ESPECIAL)
        session.add(cine)
        session.flush()
        cine_ventana = cine.id

        def peli(nombre, nota, estreno, sesion, especial=False, votos=10**6):
            p = Pelicula(titulo=f"Chknl {sufijo} {nombre}", tmdb_id=-int(uuid.uuid4().int % 10**9) - 1, generos="Drama",
                         nota_tmdb=nota, votos=votos, fecha_estreno=estreno)
            session.add(p)
            session.flush()
            session.add(Pase(pelicula_id=p.id, cine_id=cine.id, fecha_hora=sesion, es_evento_especial=especial,
                             idioma="VOSE"))
            pelis_ventana.append(p.id)
            return p.titulo

        T = dict(
            e_viernes=peli("estreno viernes", 7.0, dia(4), datetime.combine(dia(4), time(20))),
            e_domingo=peli("estreno domingo", 8.0, dia(6), datetime.combine(dia(6), time(22))),  # último día: entra
            e_lunes_sig=peli("estreno lunes siguiente", 9.0, dia(7), datetime.combine(dia(7), time(18))),
            e_anterior=peli("estreno semana anterior", 9.5, dia(-3), datetime.combine(dia(1), time(18))),
            e_oculto=peli("estreno oculto", 9.9, dia(4), datetime.combine(dia(4), time(18))),
            s_martes=peli("especial martes", 8.5, date(1960, 1, 1), datetime.combine(dia(1), time(20)), True),
            s_lunes_manana=peli("especial lunes 11h", 8.9, date(1961, 1, 1), datetime.combine(dia(0), time(11)), True),
            s_martes_sig=peli("especial martes siguiente", 8.7, date(1962, 1, 1), datetime.combine(dia(8), time(20)), True),
        )
        session.add(PeliculaOculta(pelicula_id=pelis_ventana[4], motivo="check_newsletter"))
        session.commit()

    def titulos(envio):
        with Session(engine) as session:
            n = contenido.datos_semana(session, envio)
        return (n["desde"], n["hasta"]), [f["titulo"] for f in n["estrenos"]], [f["titulo"] for f in n["especiales"]]

    lunes = contenido.momento_envio(dia(0))
    assert lunes == datetime(2031, 1, 6, 16, 0) and lunes.weekday() == 0
    rango_l, estrenos_l, especiales_l = titulos(lunes)
    assert rango_l == (dia(0), dia(6)), rango_l
    assert estrenos_l == [T["e_domingo"], T["e_viernes"]], estrenos_l  # por nota; sin el oculto ni los de fuera
    assert especiales_l == [T["s_martes"]], especiales_l  # el de las 11:00 ya ha pasado a las 16:00
    print("OK: envío en lunes -> lunes a domingo, por nota, sin ocultas ni sesiones ya pasadas")

    miercoles = contenido.momento_envio(dia(2))
    rango_m, estrenos_m, especiales_m = titulos(miercoles)
    assert rango_m == (dia(2), dia(8)), rango_m  # miércoles a martes: 7 días desde el envío, no la semana natural
    assert estrenos_m == [T["e_lunes_sig"], T["e_domingo"], T["e_viernes"]], estrenos_m
    assert especiales_m == [T["s_martes_sig"]], especiales_m
    with Session(engine) as session:  # las páginas no cambian: semana natural (lunes 6 a domingo 12)
        pagina = d.leer_pagina(session, d.seleccionar_estrenos, 0, miercoles)
    nuestras = [x["pelicula"].titulo for x in pagina["peliculas"] if x["pelicula"].id in pelis_ventana]
    assert (pagina["desde"], pagina["hasta"]) == (dia(0), dia(6)) and nuestras == [T["e_domingo"], T["e_viernes"]], nuestras
    print("OK: envío en miércoles -> miércoles a martes; /estrenos sigue en su semana natural")

    salida = "/tmp/chk_nl_fecha.html"
    assert enviar.main(["--dry-run", "--fecha", "2031-01-06", "--salida", salida]) == "dry-run"
    html_fecha = Path(salida).read_text(encoding="utf-8")
    assert T["e_viernes"] in html_fecha and T["e_lunes_sig"] not in html_fecha and "del 6 de enero al 12 de enero" in html_fecha
    try:
        enviar.main(["--fecha", "2031-01-06"])
        raise AssertionError("--fecha sin --dry-run no debe enviar")
    except SystemExit as e:
        assert e.code == 2, e
    print("OK: --dry-run --fecha 2031-01-06 usa esa ventana; --fecha sin --dry-run se rechaza")

    # --- Doble opt-in: queda pendiente, llega el correo y el enlace lo activa una sola vez ---
    A = mail("a")
    codigo, cuerpo = suscribir("  " + A.upper() + " ")
    assert (codigo, json.loads(cuerpo)) == (200, rutas.RESPUESTA), (codigo, cuerpo)
    s = fila(A)
    assert s.email == A and s.estado == "pendiente" and s.token_confirmacion and s.token_baja, s
    assert len(falso.enviados) == 1 and falso.enviados[0]["to"] == [A], falso.enviados
    c = falso.enviados[0]
    assert "List-Unsubscribe" not in c.get("headers", {}) and c["reply_to"] == correo.contacto() and c["text"], c
    assert f"https://api.ejemplo.test/newsletter/confirmar?token={s.token_confirmacion}" in c["html"]
    print("OK: suscribir deja pendiente y envía la confirmación (en minúsculas, sin espacios)")

    codigo, _, cab = llamar("GET", f"/newsletter/confirmar?token={token_de(c)}")
    assert codigo == 303 and cab["location"] == f"{plantilla.SITIO}/newsletter/confirmada", (codigo, cab)
    s = fila(A)
    assert s.estado == "activo" and s.confirmado_en and s.token_confirmacion is None, s
    codigo, _, cab = llamar("GET", f"/newsletter/confirmar?token={token_de(c)}")
    assert codigo == 303 and cab["location"].endswith("/newsletter/confirmada?error=token"), cab
    print("OK: confirmar activa y el enlace no vale dos veces")

    # --- La misma respuesta exista o no el email (nuevo, pendiente, activo, trampa) ---
    rutas._peticiones.clear()
    respuestas = {suscribir(e, ip=f"10.1.0.{i}") for i, e in enumerate([mail("nuevo"), mail("nuevo"), A, A])}
    respuestas.add(suscribir(mail("bot"), ip="10.1.1.1", web="https://spam.example"))
    assert len(respuestas) == 1, respuestas
    codigo, cuerpo = respuestas.pop()
    assert codigo == 200 and json.loads(cuerpo) == rutas.RESPUESTA, (codigo, cuerpo)
    assert fila(mail("bot")) is None, "el campo trampa no crea suscriptor"
    assert not any(e["to"] == [A] for e in falso.enviados[1:]), "a un activo no se le reenvía nada"
    print("OK: respuesta idéntica para email nuevo, pendiente, activo y bot del campo trampa")

    codigo, _ = suscribir("no-es-un-email", ip="10.1.2.1")
    assert codigo == 422, codigo
    print("OK: email mal formado -> 422")

    # --- Límites: por IP (429), por email (silencioso), reenvío cada 10 min y tope de confirmaciones ---
    rutas._peticiones.clear()
    codigos = [suscribir(mail(f"ip{i}"), ip="10.2.0.1")[0] for i in range(rutas.LIMITE_IP[0] + 1)]
    assert codigos == [200] * rutas.LIMITE_IP[0] + [429], codigos
    assert suscribir(mail("otra-ip"), ip="10.2.0.2")[0] == 200
    print("OK: límite por IP -> 429 solo para esa IP")

    rutas._peticiones.clear()
    B = mail("b")
    antes = len(falso.enviados)
    assert suscribir(B, ip="10.3.0.1")[0] == 200 and len(falso.enviados) == antes + 1
    token_b = fila(B).token_confirmacion
    assert suscribir(B, ip="10.3.0.2")[0] == 200 and len(falso.enviados) == antes + 1, "reenvío antes de 10 min"
    cambiar(B, confirmacion_enviada_en=datetime.now(timezone.utc) - timedelta(minutes=11))
    assert suscribir(B, ip="10.3.0.3")[0] == 200 and len(falso.enviados) == antes + 2, "reenvío pasados 10 min"
    assert fila(B).token_confirmacion == token_b and token_de(falso.enviados[-1]) == token_b, "mismo enlace"
    assert suscribir(B, ip="10.3.0.4") == suscribir(mail("nuevo2"), ip="10.3.0.5")
    cambiar(B, confirmacion_enviada_en=datetime.now(timezone.utc) - timedelta(hours=2))
    rutas._peticiones.clear()
    antes = len(falso.enviados)
    assert suscribir(B, ip="10.3.0.6")[0] == 200 and len(falso.enviados) == antes + 1, "otra hora, otro reenvío"
    print("OK: reenvío a pendientes como mucho cada 10 minutos y con el mismo enlace")

    rutas._peticiones.clear()
    E = mail("e")
    for i in range(rutas.LIMITE_EMAIL[0]):  # 1 envío y 2 frenadas por el reenvío cada 10 min
        suscribir(E, ip=f"10.4.0.{i}")
    cambiar(E, confirmacion_enviada_en=datetime.now(timezone.utc) - timedelta(hours=1))
    antes = len(falso.enviados)
    assert suscribir(E, ip="10.4.0.9")[0] == 200 and len(falso.enviados) == antes, "límite por email"
    assert fila(E).confirmaciones_enviadas == 1, fila(E)
    rutas._peticiones.clear()
    assert suscribir(E, ip="10.4.0.10")[0] == 200 and len(falso.enviados) == antes + 1, "era el límite por email"
    rutas._peticiones.clear()
    cambiar(B, confirmaciones_enviadas=rutas.CONFIRMACIONES_MAX,
            confirmacion_enviada_en=datetime.now(timezone.utc) - timedelta(days=1))
    antes = len(falso.enviados)
    assert suscribir(B, ip="10.4.1.1")[0] == 200 and len(falso.enviados) == antes, "tope de confirmaciones"
    print("OK: límite por email y tope de correos de confirmación (sin cambiar la respuesta)")

    rutas._peticiones.clear()
    falso.fallar = True
    assert suscribir(mail("resend-caido"), ip="10.5.0.1") == suscribir(A, ip="10.5.0.2")
    falso.fallar = False
    print("OK: si Resend falla, la respuesta es la misma")

    # --- Bajas: GET y POST (un clic), tokens inválidos ---
    C = mail("c")
    suscribir(C, ip="10.6.0.1")
    llamar("GET", f"/newsletter/confirmar?token={fila(C).token_confirmacion}")
    token_baja_c = fila(C).token_baja
    codigo, cuerpo, _ = llamar("POST", f"/newsletter/baja?token={token_baja_c}")
    assert codigo == 200 and fila(C).estado == "baja" and fila(C).baja_en, (codigo, cuerpo)
    assert llamar("POST", f"/newsletter/baja?token={token_baja_c}")[0] == 200, "baja idempotente"
    codigo, _, cab = llamar("GET", f"/newsletter/baja?token={fila(A).token_baja}")
    assert codigo == 303 and cab["location"] == f"{plantilla.SITIO}/newsletter/baja" and fila(A).estado == "baja", cab
    codigo, _, cab = llamar("GET", "/newsletter/baja?token=" + "x" * 40)
    assert codigo == 303 and cab["location"].endswith("/newsletter/baja?error=token"), cab
    assert llamar("POST", "/newsletter/baja?token=" + "x" * 40)[0] == 404
    assert llamar("POST", "/newsletter/baja?token=corto")[0] == 422
    assert llamar("GET", "/newsletter/baja")[0] == 422
    assert llamar("GET", "/newsletter/confirmar?token=" + "y" * 40)[2]["location"].endswith("?error=token")
    print("OK: baja por GET y POST, idempotente; tokens inválidos o ausentes no tocan nada")

    # Volver a suscribirse tras la baja exige otra vez confirmar
    rutas._peticiones.clear()
    antes = len(falso.enviados)
    suscribir(C, ip="10.6.0.2")
    assert fila(C).estado == "pendiente" and len(falso.enviados) == antes + 1, fila(C)
    print("OK: tras la baja, volver a suscribirse pide confirmar de nuevo")

    # --- Envío semanal: solo a activos, idempotente por semana y por hora ---
    D = mail("d")
    suscribir(D, ip="10.7.0.1")
    llamar("GET", f"/newsletter/confirmar?token={fila(D).token_confirmacion}")
    # Estado: A baja, B pendiente, C pendiente (tras baja), D activo
    datos = dict(desde=date(2031, 1, 6), hasta=date(2031, 1, 12), especiales=[], estrenos=[dict(
        id=1, titulo="Película de prueba", anio=2031, poster="https://image.tmdb.org/t/p/w342/x.jpg", cines=2,
        cine="Cine de prueba", fecha_hora=datetime(2031, 1, 10, 20, 30), vose=True)])
    enviar.datos_semana = lambda session, ahora: datos
    os.environ.pop("API_URL_PUBLICA")
    try:
        enviar.main([], ahora=LUNES_16)
        raise AssertionError("sin API_URL_PUBLICA no debe enviar")
    except SystemExit as e:
        assert "API_URL_PUBLICA" in str(e), e
    os.environ["API_URL_PUBLICA"] = "https://api.ejemplo.test"
    with Session(engine) as session:
        session.exec(delete(NewsletterEnvio).where(NewsletterEnvio.semana == SEMANA_TEST))  # por si quedó de antes
        session.commit()

    for momento in (LUNES_16.replace(hour=15), LUNES_16.replace(hour=17), LUNES_16 + timedelta(days=1)):
        assert enviar.main([], ahora=momento) == "no-toca", momento
    antes = len(falso.enviados)
    assert enviar.main(["--dry-run", "--salida", "/tmp/chk_nl.html"], ahora=LUNES_16) == "dry-run"
    assert len(falso.enviados) == antes and "Película de prueba" in Path("/tmp/chk_nl.html").read_text(encoding="utf-8")
    print("OK: fuera del lunes a las 16 no envía; --dry-run no envía y escribe el HTML")

    assert enviar.main([], ahora=LUNES_16) == "enviada"
    semanales = falso.enviados[antes:]
    para = {c["to"][0] for c in semanales}
    assert D in para and not {A, B, C} & para, para
    c = next(c for c in semanales if c["to"] == [D])
    url = f"https://api.ejemplo.test/newsletter/baja?token={fila(D).token_baja}"
    assert c["headers"] == {"List-Unsubscribe": f"<{url}>", "List-Unsubscribe-Post": "List-Unsubscribe=One-Click"}, c
    assert url in c["html"] and url in c["text"] and c["from"] == correo.remitente() and c["reply_to"] == correo.contacto()
    with Session(engine) as session:
        envio = session.exec(select(NewsletterEnvio).where(NewsletterEnvio.semana == SEMANA_TEST)).one()
        assert envio.destinatarios == len(semanales) == envio.ok and envio.errores == 0, envio
    print(f"OK: enviada solo a activos ({len(semanales)}), con List-Unsubscribe y su enlace de baja; queda registrada")

    assert enviar.main([], ahora=LUNES_16 + timedelta(minutes=50)) == "ya-enviada"
    assert len(falso.enviados) == antes + len(semanales)
    assert enviar.main(["--forzar"], ahora=LUNES_16 + timedelta(days=2)) == "enviada"
    assert len(falso.enviados) == antes + 2 * len(semanales)
    datos["estrenos"] = []
    assert enviar.main(["--forzar"], ahora=LUNES_16) == "vacia"
    print("OK: la misma semana no se envía dos veces (salvo --forzar) y una semana vacía no se envía")

    # Lotes: de 100 en 100; un lote fallido no para los demás
    class Intermitente(CorreoFalso):
        def enviar_lote(self, cs):
            if len(self.lotes) == 1 and not getattr(self, "fallado", False):
                self.fallado = True
                raise RuntimeError("lote 2 falla")
            return super().enviar_lote(cs)
    inter = Intermitente()
    ok, errores = correo.enviar_por_lotes([{"to": [f"x{i}@ejemplo.test"]} for i in range(250)], inter)
    assert (ok, errores) == (150, 100) and [len(l) for l in inter.lotes] == [100, 50], (ok, errores, inter.lotes)
    print("OK: envío por lotes de 100; un lote fallido cuenta como errores y se sigue")

    # --- Plantilla: < 100 KB con el máximo de películas, alt en cada imagen, escapada, 600 px ---
    largo = lambda i: dict(id=i, titulo=f"Título larguísimo número {i} <script>alert(1)</script> & más " * 2,
                           anio=2026, poster=f"https://image.tmdb.org/t/p/w342/p{i}.jpg", cines=12,
                           cine="Cine con un nombre bastante largo", fecha_hora=datetime(2031, 1, 9, 22, 45), vose=i % 2 == 0)
    lleno = dict(desde=date(2031, 1, 6), hasta=date(2031, 1, 12),
                 estrenos=[largo(i) for i in range(contenido.MAX_ESTRENOS)],
                 especiales=[largo(i) for i in range(10, 10 + contenido.MAX_ESPECIALES)])
    asunto, html, texto = plantilla.semanal(lleno, correo.url_baja("t" * 43), correo.contacto())
    imagenes = re.findall(r"<img\b[^>]*>", html)
    assert len(html.encode()) < 100_000, len(html.encode())
    assert len(imagenes) == 10 and all(re.search(r'alt="Póster de [^"]+"', i) for i in imagenes), imagenes
    assert "<script>" not in html and "&lt;script&gt;" in html
    assert 'width="600"' in html and 'bgcolor="#f4f1fb"' in html and plantilla.MORADO in html
    assert "<link" not in html and "This product uses the TMDB API but is not endorsed or certified by TMDB." in html
    assert html.count("https://fps24.es/pelicula/") >= 10 and "/privacidad" in html and correo.contacto() in html
    assert "<script>" in texto and "Darte de baja: " in texto  # el texto plano no se escapa: no es HTML
    print(f"OK: plantilla de {len(html.encode()) / 1024:.1f} KB con 6 estrenos y 4 especiales, alt en las 10 imágenes")

    assert contenido.poster_w342("https://image.tmdb.org/t/p/w500/abc.jpg") == "https://image.tmdb.org/t/p/w342/abc.jpg"
    with Session(engine) as session:
        real = contenido.datos_semana(session)
    assert len(real["estrenos"]) <= contenido.MAX_ESTRENOS and len(real["especiales"]) <= contenido.MAX_ESPECIALES
    assert all(f["poster"] is None or "/w342/" in f["poster"] for f in real["estrenos"] + real["especiales"])
    print(f"OK: contenido real de esta semana: {len(real['estrenos'])} estrenos y {len(real['especiales'])} especiales")

    # --- Admin: vista previa, prueba solo al admin y recuento de activos ---
    CORREO_ADMIN = f"Admin-NL-{sufijo}@Ejemplo.test"
    os.environ["ADMIN_EMAILS"] = CORREO_ADMIN
    actual = {"u": None}
    app.dependency_overrides[admin.usuario_o_nada] = lambda: actual["u"]
    for u in (None, Usuario(id=str(uuid.uuid4()), email=mail("normal"))):
        actual["u"] = u
        assert llamar("GET", "/admin/newsletter/vista-previa")[0] == 404
        assert llamar("POST", "/admin/newsletter/enviar-prueba")[0] == 404
    actual["u"] = Usuario(id=str(uuid.uuid4()), email=CORREO_ADMIN)
    codigo, cuerpo, cab = llamar("GET", "/admin/newsletter/vista-previa")
    assert codigo == 200 and cab["content-type"].startswith("text/html") and b"Esta semana en Madrid" in cuerpo, codigo
    for fecha, dentro, fuera in (("2031-01-06", T["e_viernes"], T["e_lunes_sig"]), ("2031-01-08", T["e_lunes_sig"], T["e_anterior"])):
        html_admin = llamar("GET", f"/admin/newsletter/vista-previa?fecha={fecha}")[1].decode()
        assert dentro in html_admin and fuera not in html_admin, fecha
    assert llamar("GET", "/admin/newsletter/vista-previa?fecha=no-es-fecha")[0] == 422
    antes = len(falso.enviados)
    codigo, cuerpo, _ = llamar("POST", "/admin/newsletter/enviar-prueba", {"to": "otro@ejemplo.test"})
    assert codigo == 200 and json.loads(cuerpo) == {"enviado_a": CORREO_ADMIN.lower()}, cuerpo
    assert [c["to"] for c in falso.enviados[antes:]] == [[CORREO_ADMIN.lower()]], falso.enviados[antes:]
    assert falso.enviados[-1]["subject"].startswith("[Prueba]")
    falso.fallar = True
    assert llamar("POST", "/admin/newsletter/enviar-prueba")[0] == 502
    falso.fallar = False
    resumen = json.loads(llamar("GET", "/admin/resumen")[1])
    with Session(engine) as session:
        activos = session.exec(text("SELECT count(*) FROM suscriptor WHERE estado = 'activo'")).scalar()
    assert resumen["suscriptores_activos"] == activos >= 1, (resumen, activos)
    print("OK: admin: vista previa en HTML, prueba solo a su email, 404 al resto y suscriptores_activos en el resumen")

    # --- RLS ---
    with engine.connect() as conn:
        rls = dict(conn.execute(text("SELECT relname, relrowsecurity FROM pg_class WHERE relnamespace = "
                                     "'public'::regnamespace AND relname IN ('suscriptor', 'newsletter_envio')")).all())
    assert rls == {"suscriptor": True, "newsletter_envio": True}, rls
    print("OK: RLS activado en suscriptor y newsletter_envio")
finally:
    with Session(engine) as session:
        session.exec(delete(Suscriptor).where(Suscriptor.email.like(f"chk-nl-{sufijo}-%")))
        session.exec(delete(NewsletterEnvio).where(NewsletterEnvio.semana == SEMANA_TEST))
        if pelis_ventana:
            session.exec(delete(PeliculaOculta).where(PeliculaOculta.pelicula_id.in_(pelis_ventana)))
            session.exec(delete(Pase).where(Pase.pelicula_id.in_(pelis_ventana)))
            session.exec(delete(Pelicula).where(Pelicula.id.in_(pelis_ventana)))
        if cine_ventana:
            session.exec(delete(Cine).where(Cine.id == cine_ventana))
        session.commit()
    app.dependency_overrides.clear()

assert all("@ejemplo.test" in c["to"][0].lower() for c in falso.enviados), "solo direcciones de prueba"
print("OK: check_newsletter (ningún correo real enviado)")
