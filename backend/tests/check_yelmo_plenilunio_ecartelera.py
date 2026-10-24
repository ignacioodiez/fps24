"""Self-check de Yelmo Plenilunio en eCartelera con una muestra de HTML guardada. No toca la red ni la BD.
Uso: docker compose exec api python tests/check_yelmo_plenilunio_ecartelera.py"""
import sys
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.scrapers import plataforma_ecartelera as ec
from app.scrapers.cines import yelmo_plenilunio_ecartelera as yp
from app.services.cines import CINES_CONOCIDOS, CINES_DATOS

MUESTRA = (Path(__file__).resolve().parent / "muestras" / "ecartelera_yelmo_plenilunio.html").read_text(encoding="utf-8")
HOY = date(2026, 10, 24)  # el día de la muestra


def contadores():
    return {"creado": 0, "actualizado": 0, "descartado": 0, "peticiones": 0}


# --- un día: todo en Español, también lo que por país sería VOSE ---
c = contadores()
sesiones = ec.leer_dia(MUESTRA, HOY, c, yp.CINES[0], yp.IDIOMA)
assert Counter(s.titulo for s in sesiones) == {"Arriba Tutto": 4, "Clayface": 6, "Coyote contra Acme": 1,
                                               "En el corazón de la bestia": 3}, sesiones
assert {s.idioma for s in sesiones} == {"Español"} and c["descartado"] == 0
assert {s.idioma for s in ec.leer_dia(MUESTRA, HOY, contadores(), yp.CINES[0]) if s.titulo == "Clayface"} == {"VOSE"}  # sin IDIOMA, el país
assert ec.leer_dias(MUESTRA, yp.ID_ECARTELERA) == list(range(10))
print("OK: un día")

# --- todos los días: su ficha, pausa entre peticiones, nunca /comprar/ ---
pedidas, pausas = [], []


def obtener(url):
    pedidas.append(url)
    d = HOY + timedelta(days=int(url.split(",")[1]))
    return MUESTRA.replace('title="Cartelera del S&aacute;bado 24">S&aacute;bado 24</a>', f'>Día {d.day:02d}</a>', 1)


sesiones = ec.leer_cine(yp.ID_ECARTELERA, yp.CINES[0], contadores(), yp.IDIOMA, obtener=obtener, dormir=pausas.append, hoy=HOY)
assert pedidas == [f"https://www.ecartelera.com/cines/517,{n},1.html" for n in range(10)], pedidas
assert pausas == [ec.PAUSA] * 9 and len(sesiones) == 140 and {s.idioma for s in sesiones} == {"Español"}
assert not any("/comprar/" in u or "awin" in u for u in pedidas)
print("OK: todos los días")

# --- alta del cine ---
slug = CINES_CONOCIDOS[yp.CINES[0]]
assert slug == "yelmo-plenilunio" and CINES_DATOS[slug]["tarifas"] is None
assert CINES_DATOS[slug]["web"] == yp.LINK_COMPRA and yp.LINK_COMPRA.startswith("https://yelmocines.es/")
print("OK: alta")
