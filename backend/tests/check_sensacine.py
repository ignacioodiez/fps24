"""Self-check de SensaCine: normalización del JSON, idioma, paginación/nextDate y aislamiento de fallos por cine.
No toca la red ni la BD. Uso: docker compose exec api python tests/check_sensacine.py"""
import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.scrapers import plataforma_sensacine as ps
from app.scrapers.cines import sensacine
from app.scrapers.comun import FuenteNoDisponible


def showtime(hora, *enlaces, tags=("Localization.Language.Spanish",)):
    return {"startsAt": f"2026-10-23T{hora}:00", "tags": list(tags), "data": {"ticketing": [{"provider": p, "urls": [u]} for p, u in enlaces]}}


RELAY = "https://relay.mvtx.us/ticketing/dbz?code_theater=E0609&perft=11:30&code="
# Recorte de una respuesta real de /_/showtimes/theater-E0609/d-2026-10-23/
PAGINA = {
    "error": False, "nextDate": None, "pagination": {"page": 1, "totalPages": 1},
    "results": [
        {"movie": {"title": "Sentido y sensibilidad", "data": {"productionYear": 2026}},
         "showtimes": {"local": [], "original_st": [
             showtime("11:30", ("relay", RELAY + "V.O. SUB. CASTELLANO"), ("default", "https://verdimadrid.admit-one.eu/seats/135940")),
             showtime("18:05", ("relay", RELAY + "V.O. SUB. CASTELLANO")),
         ]}},
        {"movie": {"title": "La Bola Negra", "data": {"productionYear": 2026}},
         "showtimes": {"dubbed_st": [showtime("16:00", ("relay", RELAY + "V.O. SUB. INGLÉS"))],
                       "local": [showtime("20:30")]}},
        {"movie": None, "showtimes": {"dubbed": [showtime("12:00"), showtime("17:00")]}},
        # Artistic Metropol: todo en dubbed y sin tags de idioma; la versión solo está en su enlace
        {"movie": {"title": "Palestina 36", "data": {"productionYear": 2025}}, "showtimes": {"dubbed": [
            showtime("19:00", ("default", "https://artisticmetropol.es/sesion/sala-1-palestina-36-2025-v-o-s-e/"),
                     tags=["Format.Projection.Digital"]),
            showtime("21:00", ("default", "https://artisticmetropol.es/sesion/sala-1-sus-hijos-2026-doblada-al-espanol-7/"),
                     tags=["Format.Projection.Digital"])]}},
        {"movie": {"title": "Rota", "data": None}, "showtimes": {"local": [{"startsAt": "mañana"}]}},
    ],
}


def contadores():
    return {"creado": 0, "actualizado": 0, "descartado": 0, "sin_titulo": 0, "peticiones": 0}


# --- normalización ---
c = contadores()
sesiones = ps.normalizar_pagina(PAGINA, "E0609", c)
assert [(s.titulo, s.anio, s.fecha_hora.strftime("%H:%M"), s.idioma) for s in sesiones] == [
    ("Sentido y sensibilidad", 2026, "11:30", "VOSE"),
    ("Sentido y sensibilidad", 2026, "18:05", "VOSE"),
    ("La Bola Negra", 2026, "16:00", "Español"),
    ("La Bola Negra", 2026, "20:30", "Español"),
    ("Palestina 36", 2025, "19:00", "VOSE"),
    ("Palestina 36", 2025, "21:00", "Español"),
], sesiones
assert sesiones[0].fecha_hora == datetime(2026, 10, 23, 11, 30)
assert sesiones[0].link == "https://verdimadrid.admit-one.eu/seats/135940"     # admit-one ("default") primero
assert sesiones[1].link.startswith("https://relay.mvtx.us/")                     # si no, el primer enlace
assert sesiones[3].link == "https://www.sensacine.com/cines/cine/E0609/"         # sin enlaces: la ficha del cine
assert c["sin_titulo"] == 2 and c["descartado"] == 1, c
print("OK: normalización")

# --- idioma ---
T = ["Localization.Language.Spanish"]
assert ps.idioma_de("original_st", None, T) == "VOSE" and ps.idioma_de("original", None, T) == "VOSE"
assert ps.idioma_de("local", "CASTELLANO", T) == "Español" and ps.idioma_de("dubbed", "CONCIERTO", T) == "Español"
assert ps.idioma_de("dubbed_st", "V.O. SUB. INGLÉS", T) == "Español"
assert ps.idioma_de("dubbed_st", "V.O. SUB. CASTELLANO", T) == "VOSE"
assert ps.idioma_de("dubbed_st", None, T) == "Español"
assert ps.idioma_de("dubbed", None, ["Format.Projection.Digital"], "https://x/sala-2-la-esfinge-1981-v-o-s-e-2/") == "VOSE"
assert ps.idioma_de("original_st", None, [], "https://cine.entradas.com/evento/3744/") == "VOSE"
assert ps.idioma_de("dubbed", None, [], "https://cine.entradas.com/evento/3744/") == "Español"
print("OK: idioma")


# --- paginación y nextDate ---
def respuesta(n_sesiones, total_paginas=1, siguiente=None):
    # Como la web real: los días vacíos llevan error=true y un mensaje que no es un fallo
    vacio = "next.showtime.on" if siguiente else "no.showtime.error"
    return {"error": not n_sesiones, "message": None if n_sesiones else vacio, "nextDate": siguiente, "pagination": {"totalPages": total_paginas},
            "results": [{"movie": {"title": "X", "data": {"productionYear": 2026}},
                         "showtimes": {"local": [showtime(f"1{i}:00") for i in range(n_sesiones)]}}] if n_sesiones else []}


HOY = date(2026, 10, 22)
base = "https://www.sensacine.com/_/showtimes/theater-E0609/"
web = {
    base + "d-2026-10-22/": respuesta(2, total_paginas=2),
    base + "d-2026-10-22/p-2/": respuesta(1, total_paginas=2),
    base + "d-2026-10-23/": respuesta(0, total_paginas=0, siguiente="2026-10-30"),
    base + "d-2026-10-30/": respuesta(1),
    base + "d-2026-11-04/": respuesta(1),  # tras 4 días vacíos sin nextDate: sigue pidiendo
}
pedidas, pausas = [], []


def obtener(url):
    pedidas.append(url)
    return web.get(url, respuesta(0, total_paginas=0))


c = contadores()
sesiones = ps.leer_cine("E0609", c, obtener=obtener, dormir=pausas.append, hoy=HOY)
assert pedidas[:4] == [base + "d-2026-10-22/", base + "d-2026-10-22/p-2/", base + "d-2026-10-23/", base + "d-2026-10-30/"], pedidas[:4]
assert base + "d-2026-10-24/" not in pedidas                       # nextDate se salta el hueco
assert pedidas[-1] == base + "d-2026-11-11/"                        # para tras FIN_TRAS_VACIOS días vacíos
assert len(sesiones) == 5 and c["peticiones"] == len(pedidas) == len(pausas) + 1 and set(pausas) == {ps.PAUSA}

try:  # tope de peticiones
    ps.leer_cine("E0609", contadores(), obtener=lambda url: respuesta(1, total_paginas=500), dormir=lambda s: None, hoy=HOY)
    raise AssertionError("sin tope de peticiones")
except FuenteNoDisponible as e:
    assert "tope" in str(e)
for rara in ({"error": True, "message": "x"}, {"results": "nada"}, ["no", "es", "un", "dict"]):
    try:
        ps.leer_cine("E0609", contadores(), obtener=lambda url: rara, dormir=lambda s: None, hoy=HOY)
        raise AssertionError(f"{rara!r} no ha fallado")
    except FuenteNoDisponible:
        pass
print("OK: paginación y nextDate")


# --- un cine que falla no impide leer los demás ---
class SesionFalsa:
    commits = 0

    def __init__(self, engine):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def commit(self):
        SesionFalsa.commits += 1


ROTO = "Sala Berlanga"
registrados = []


def leer_falso(id_cine, cont, **kw):
    if id_cine == sensacine.IDS[ROTO]:
        raise FuenteNoDisponible("HTTP 429")
    return [ps.Sesion("X", 2026, datetime(2026, 10, 23, 20, 0), "VOSE", "https://ejemplo")]


sensacine.Session = SesionFalsa
sensacine.leer_cine = leer_falso
sensacine.resolver_pelicula = lambda session, titulo, cine, anio_web=None: (1, False)
sensacine.registrar_pase = lambda session, **kw: registrados.append(kw) or "creado"
try:
    sensacine.scrapear_sensacine()
    raise AssertionError("no se lanzó la excepción")
except FuenteNoDisponible as e:
    assert ROTO in str(e), e
assert SesionFalsa.commits == 1
assert sorted(r["cine"] for r in registrados) == sorted(c for c in sensacine.CINES if c != ROTO)
assert all(r["sala"] == r["cine"] and r["precio"] == "Consultar" for r in registrados)
print("OK: fallo aislado por cine")
