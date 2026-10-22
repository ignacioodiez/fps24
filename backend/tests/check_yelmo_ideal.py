"""Self-check de la fecha y el idioma del scraper de Yelmo Ideal. No toca la red ni la BD.
Uso: docker compose exec api python tests/check_yelmo_ideal.py"""
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.scrapers.cines.yelmo_ideal import idioma_de, parsear_fecha
from app.services.tiempo import resolver_anio

assert parsear_fecha("22-octubre", "15:45") == datetime(resolver_anio(10, 22), 10, 22, 15, 45)
assert parsear_fecha("03-junio", "9:05") == datetime(resolver_anio(6, 3), 6, 3, 9, 5)
for valor, hora in (("22-octubre", "15.45"), ("22-octubrx", "15:45"), ("32-octubre", "15:45"), ("octubre", "15:45")):
    try:
        parsear_fecha(valor, hora)
        raise AssertionError((valor, hora))
    except ValueError:
        pass
assert idioma_de("2D INGLÉS SUBTITULADO EN ESPAÑOL (VOSE)") == "VOSE"
assert idioma_de("2D Español") == "Español"
print("check_yelmo_ideal OK")
