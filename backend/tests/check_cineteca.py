"""Self-check de los parsers del scraper de Cineteca. No toca la red ni la BD.
Uso: docker compose exec api python tests/check_cineteca.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.scrapers.cines.cineteca import parsear_anio, parsear_hora

assert parsear_hora("19:30 h") == (19, 30)
assert parsear_hora(" 9:05h ") == (9, 5)
assert parsear_hora("12:00") == (12, 0)
for malo in ("", "19.30 h", "Sala Plató", "19:30 h 20:00 h"):
    try:
        parsear_hora(malo)
        raise AssertionError(malo)
    except ValueError:
        pass
assert parsear_anio("Natalia Koniarz\nPolonia\n2025") == 2025
assert parsear_anio("Sin año 123") is None
print("check_cineteca OK")
