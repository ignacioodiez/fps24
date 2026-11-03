"""Self-check de los scrapers de Casa de América, Academia de Cine y Casa de México con muestras de HTML guardadas
(03/11/2026). No toca la red. Uso: docker compose exec api python tests/check_cines_culturales.py
La parte de idempotencia escribe en la BD local de verdad (dos ejecuciones con commit por cine): borra lo que crea."""
import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import delete
from sqlmodel import Session, select

from app.database.engine import engine
from app.database.models import Cine, Pase, Pelicula
from app.scrapers import comun
from app.scrapers.cines import academia_cine as ac, casa_america as ca, casa_mexico as cm
from app.services.cines import CINES_CONOCIDOS, CINES_DATOS
from app.services.pases import normalizar_idioma

MUESTRAS = Path(__file__).resolve().parent / "muestras"
leer = lambda nombre: (MUESTRAS / f"{nombre}.html").read_text(encoding="utf-8")
nada = lambda s: None

# --- Casa de América: solo CINE, día heredado del grupo anterior, precio de .condiciones ---
AGENDA = leer("casa_america_agenda")
c = {"descartado": 0}
america = ca.leer_agenda(AGENDA, c)
assert len(america) == 13 and c["descartado"] == 0, (len(america), c)
assert {s.link.split("/cine/")[1] for s in america} == {"el-deshielo", "sus-hijos", "las-locas-del-obelisco", "las-poquianchis",
                                                         "ceniza-en-la-boca", "el-tres-de-copas", "chicogrande"}
assert america[0] == ca.Sesion("El deshielo", datetime(2026, 11, 5, 18), "Entrada libre hasta completar aforo",
                               "https://www.casamerica.es/cine/el-deshielo")
# "Sus hijos" va en grupos sin cabecera: hereda el 06 y el 07 de los grupos anteriores
assert [s.fecha_hora for s in america if s.titulo == "Sus hijos"] == [datetime(2026, 11, 6, 19), datetime(2026, 11, 7, 19)]
assert {s.precio for s in america if s.titulo == "Ceniza en la boca"} == {"Consultar"}  # "Consultar precios"
assert ca.precio_de("*Excepto el viernes 23 de octubre. Consultar precios") == ca.precio_de("") == "Consultar"
try:
    ca.leer_agenda("<html></html>", c)
    raise AssertionError("página sin agenda aceptada")
except ca.FuenteNoDisponible:
    pass
assert ca.paginas(date(2026, 11, 3)) == [ca.URL, ca.URL + "/202612"] and ca.paginas(date(2026, 12, 1))[1].endswith("/202701")
print("OK: Casa de América")

# --- Academia de Cine: listado con fecha; ficha -> precio solo si es película en la sala de Madrid con entradas ---
LISTADO = leer("academia_actividades")
actividades = ac.leer_listado(LISTADO)
assert len(actividades) == 59, len(actividades)
assert actividades[0] == (ac.URL + "la-virgen-de-la-tosquera/", datetime(2026, 11, 3, 16), "La virgen de la Tosquera")
assert actividades[-1][1] == datetime(2026, 12, 9, 19)  # "09/Dic"
FICHAS_AC = {"godzilla-minus-zero": "academia_godzilla", "la-virgen-de-la-tosquera": "academia_virgen",
             "el-confidente-1": "academia_confidente", "llueve-sobre-babel": "academia_llueve",
             "en-barcelona-20-anos-de-el-laberinto-del-fauno": "academia_barcelona",
             "objetosdeafectosergiodosal": "academia_cafe"}
precio = {s: ac.leer_ficha(leer(m)) for s, m in FICHAS_AC.items()}
assert precio == {"godzilla-minus-zero": "3,15 €",  # libre para académicos | 3’15€ público general
                  "la-virgen-de-la-tosquera": "Entrada libre, previa reserva de entradas",
                  "llueve-sobre-babel": "Consultar",  # aún sin bloque de entradas (abre la venta días antes)
                  "el-confidente-1": None,  # pase exclusivo para académicos
                  "en-barcelona-20-anos-de-el-laberinto-del-fauno": None,  # en la Filmoteca de Catalunya
                  "objetosdeafectosergiodosal": None}, precio  # Café Gráfico: sin Formato
assert ac.leer_ficha(leer("academia_jornada")) is None  # jornada en la sala, sin ficha técnica

pedidas, pausas = [], []
def obtener_ac(url):
    pedidas.append(url)
    if url == ac.URL:
        return LISTADO
    slug = url.rstrip("/").rsplit("/", 1)[1]
    return leer(FICHAS_AC.get(slug, "academia_jornada"))  # las demás: como la jornada (se descartan)
c = {"descartado": 0}
academia = ac.leer_cine(c, obtener=obtener_ac, dormir=pausas.append)
assert [(s.titulo, s.fecha_hora, s.precio) for s in academia] == [
    ("La virgen de la Tosquera", datetime(2026, 11, 3, 16), "Entrada libre, previa reserva de entradas"),
    ("Godzilla Minus Zero", datetime(2026, 11, 5, 19), "3,15 €"),
    ("Llueve sobre Babel", datetime(2026, 11, 10, 16), "Consultar")], academia
assert academia[1].link == ac.URL + "godzilla-minus-zero/"
assert len(pedidas) == len(set(pedidas)) == c["peticiones"] == 60 and pausas == [ac.PAUSA] * 59 and c["descartado"] == 56
try:
    ac.leer_cine({}, obtener=lambda url: LISTADO.replace("listadoActividades-actividad-fecha", "x"), dormir=nada)
    raise AssertionError("listado sin fechas aceptado")
except ac.FuenteNoDisponible:
    pass
print("OK: Academia de Cine")

# --- Casa de México: archivo -> fichas; sesiones de .bloque-sesion; la ficha del ciclo, descartada ---
ARCHIVO = leer("casa_mexico_archivo")
fichas = cm.leer_archivo(ARCHIVO)
assert len(fichas) == 13 and fichas[0].endswith("/ciclo-de-cine-cuando-cae-la-noche/"), fichas
estela = cm.leer_ficha(leer("casa_mexico_estela"), "u")
assert [(s.titulo, s.fecha_hora, s.precio) for s in estela] == [
    ("Estela", datetime(2026, 11, 19, 19), "Gratis"), ("Estela", datetime(2026, 11, 28, 19), "Gratis")]
assert [s.titulo for s in cm.leer_ficha(leer("casa_mexico_parvulos"), "u")] == ["Párvulos: Hijos del apocalipsis"]
assert cm.leer_ficha(leer("casa_mexico_ciclo"), "u") == []  # "Múltiples sesiones": la del ciclo entero
# sin bloque SESIONES (aún sin Eventbrite): fecha de la cabecera y hora del icono del reloj
assert [(s.titulo, s.fecha_hora) for s in cm.leer_ficha(leer("casa_mexico_tekenchu"), "u")] == [
    ("Tekenchu, el ritual de los nahuales", datetime(2026, 11, 27, 19))]
FICHAS_CM = {fichas[4]: "casa_mexico_estela", fichas[2]: "casa_mexico_parvulos", fichas[1]: "casa_mexico_tekenchu"}
assert fichas[4].endswith("-estela/") and fichas[2].endswith("-parvulos-hijos-del-apocalipsis/")
# las demás fichas, como la del ciclo (sin sesiones)
obtener_cm = lambda url: ARCHIVO if url == cm.URL else leer(FICHAS_CM.get(url, "casa_mexico_ciclo"))
c = {"descartado": 0}
mexico = cm.leer_cine(c, obtener=obtener_cm, dormir=pausas.append)
assert len(mexico) == 4 and c == {"descartado": 10, "peticiones": 14}, (len(mexico), c)
assert {s.link for s in mexico} == {fichas[4], fichas[2], fichas[1]}
print("OK: Casa de México")

# --- alta de los cines y versión vacía ---
for modulo, slug in ((ca, "casa-america"), (ac, "academia-cine"), (cm, "casa-mexico")):
    assert CINES_CONOCIDOS[modulo.CINES[0]] == slug
    d = CINES_DATOS[slug]
    assert d["tipo"] == "cultural" and d["tarifas"] is None and d["telefono"] and d["web"], slug
assert normalizar_idioma(None) is None and normalizar_idioma("") is None and normalizar_idioma("V.O.S.E.") == "VOSE"
print("OK: alta y versión vacía")

# --- idempotencia en la BD local: dos ejecuciones por cine, la segunda no crea nada ---
if engine.url.host not in ("db", "localhost", "127.0.0.1"):
    sys.exit(f"Me niego: la BD no es local (host {engine.url.host!r})")

# Fechas en el futuro (las de las muestras pasarán): guardar_sesiones salta los días ya pasados
futuro = lambda sesiones: [s.__class__(s.titulo, s.fecha_hora.replace(year=2099), s.precio, s.link) for s in sesiones]
casos = [(ca, ca.scrapear_casa_america, futuro(america), ca.SALA), (ac, ac.scrapear_academia_cine, futuro(academia), ac.SALA),
         (cm, cm.scrapear_casa_mexico, futuro(mexico), cm.SALA)]
titulos = {s.titulo for _, _, sesiones, _ in casos for s in sesiones}
slugs = [CINES_CONOCIDOS[m.CINES[0]] for m, *_ in casos]
with Session(engine) as session:
    habia = set(session.exec(select(Cine.slug).where(Cine.slug.in_(slugs))).all())
    peliculas = {t: Pelicula(titulo=f"Prueba check_cines_culturales {t}") for t in titulos}
    session.add_all(peliculas.values())
    session.commit()
    ids = {t: p.id for t, p in peliculas.items()}

resolver_original = comun.resolver_pelicula
comun.resolver_pelicula = lambda session, titulo, cine: (ids[titulo], False)
originales = {m: m.leer_cine for m, *_ in casos}
try:
    for modulo, scrapear, sesiones, sala in casos:
        pasado = sesiones[0].__class__(sesiones[0].titulo, datetime(2000, 1, 1, 18), "Gratis", "x")
        modulo.leer_cine = lambda contadores, sesiones=sesiones, pasado=pasado: [pasado, *sesiones]  # el pasado no entra
        primera, segunda = scrapear(), scrapear()
        n = len(sesiones)
        assert (primera["creado"], primera["actualizado"]) == (n, 0), (modulo.__name__, primera)
        assert (segunda["creado"], segunda["actualizado"]) == (0, n), (modulo.__name__, segunda)
        with Session(engine) as session:
            cine_id = session.exec(select(Cine.id).where(Cine.slug == CINES_CONOCIDOS[modulo.CINES[0]])).one()
            pases = session.exec(select(Pase).where(Pase.pelicula_id.in_(ids.values()), Pase.cine_id == cine_id)).all()
            assert len(pases) == n and {p.sala for p in pases} == {sala} and {p.idioma for p in pases} == {None}, modulo.__name__
            assert {p.precio for p in pases} == {s.precio for s in sesiones} and all(p.link_compra for p in pases)
        print(f"OK: {modulo.__name__.rsplit('.', 1)[1]} idempotente ({n} pases sin versión, la segunda vez 0 creados)")
finally:
    comun.resolver_pelicula = resolver_original
    for modulo, leer_cine in originales.items():
        modulo.leer_cine = leer_cine
    with Session(engine) as session:
        session.exec(delete(Pase).where(Pase.pelicula_id.in_(ids.values())))
        session.exec(delete(Pelicula).where(Pelicula.id.in_(ids.values())))
        session.exec(delete(Cine).where(Cine.slug.in_(set(slugs) - habia)))
        session.commit()
