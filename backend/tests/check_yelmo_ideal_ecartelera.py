"""Self-check del parser de eCartelera para Yelmo Ideal con una muestra de HTML guardada. No toca la red ni la BD.
Uso: docker compose exec api python tests/check_yelmo_ideal_ecartelera.py"""
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.scrapers import plataforma_ecartelera as ec
from app.scrapers.cines import yelmo_ideal_ecartelera as ye
from app.scrapers.comun import FuenteNoDisponible

MUESTRA = (Path(__file__).resolve().parent / "muestras" / "ecartelera_yelmo_ideal.html").read_text(encoding="utf-8")
HOY = date(2026, 10, 24)  # el día de la muestra


def contadores():
    return {"creado": 0, "actualizado": 0, "descartado": 0, "peticiones": 0}


# --- un día ---
c = contadores()
sesiones = ec.leer_dia(MUESTRA, HOY, c, ye.CINES[0])
assert [(s.titulo, s.fecha_hora.strftime("%H:%M"), s.idioma) for s in sesiones] == [
    ("Arriba Tutto", "17:40", "Español"),   # España
    ("Blue Heron", "20:40", "VOSE"),        # Canadá
    ("Clayface", "15:45", "VOSE"),
    ("Clayface", "18:05", "VOSE"),
    ("Clayface", "20:25", "VOSE"),
    ("Clayface", "22:45", "VOSE"),
], sesiones                                 # Coyote contra Acme no tiene pases ese día
assert sesiones[0].fecha_hora == datetime(2026, 10, 24, 17, 40) and c["descartado"] == 0
assert ec.leer_dias(MUESTRA, ye.ID_ECARTELERA) == list(range(10))
assert ec.leer_dias(MUESTRA, 517) == []  # solo los días de este cine
try:  # la página no es del día que se espera
    ec.leer_dia(MUESTRA, date(2026, 10, 25), contadores(), ye.CINES[0])
    raise AssertionError("no ha fallado con otro día")
except FuenteNoDisponible:
    pass
c = contadores()
assert ec.leer_dia(MUESTRA.replace('data-session-time="17:40"', 'data-session-time="25:99"'), HOY, c, ye.CINES[0])[0].titulo == "Blue Heron"
assert c["descartado"] == 1
print("OK: un día")


# --- todos los días: una petición por día, pausa entre ellas, nunca /comprar/ ---
def pagina_de(n):
    d = HOY + timedelta(days=n)
    return MUESTRA.replace('<li class="on"><a href="https://www.ecartelera.com/cines/54,0,1.html" title="Cartelera del S&aacute;bado 24">S&aacute;bado 24</a>',
                           f'<li class="on"><a href="x">Día {d.day:02d}</a>')


pedidas, pausas = [], []


def obtener(url):
    pedidas.append(url)
    return pagina_de(int(url.split(",")[1]))


c = contadores()
sesiones = ec.leer_cine(ye.ID_ECARTELERA, ye.CINES[0], c, obtener=obtener, dormir=pausas.append, hoy=HOY)
assert pedidas == [f"https://www.ecartelera.com/cines/54,{n},1.html" for n in range(10)], pedidas
assert c["peticiones"] == 10 and pausas == [ec.PAUSA] * 9 and ec.PAUSA >= 2
assert len(sesiones) == 60 and {s.fecha_hora.date() for s in sesiones} == {HOY + timedelta(days=n) for n in range(10)}
assert not any("/comprar/" in u or "awin" in u for u in pedidas)
try:
    ec.leer_cine(ye.ID_ECARTELERA, ye.CINES[0], contadores(), obtener=lambda url: "<html>sin cartelera</html>", dormir=lambda s: None, hoy=HOY)
    raise AssertionError("no ha fallado sin cartelera")
except FuenteNoDisponible:
    pass
print("OK: todos los días")
