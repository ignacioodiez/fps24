"""Self-check de la sede y la fecha del scraper de Embajadores. No toca la red ni la BD.
Uso: docker compose exec api python tests/check_embajadores.py"""
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.scrapers.cines.embajadores import cine_de, parsear_fecha_hora
from app.services.tiempo import resolver_anio

assert cine_de("Cines Embajadores") == "Cine Embajadores"
assert cine_de("Cine Embajadores Río") == "Cine Embajadores Río"
assert cine_de("Embajadores Rio") == "Cine Embajadores Río"
assert cine_de("") == "Cine Embajadores"

assert parsear_fecha_hora("23/10", "17:30") == datetime(resolver_anio(10, 23), 10, 23, 17, 30)
for malo in (("", "17:30"), ("23/10", "17h"), ("32/10", "17:30")):
    try:
        parsear_fecha_hora(*malo)
        raise AssertionError(malo)
    except ValueError:
        pass
print("check_embajadores OK")
