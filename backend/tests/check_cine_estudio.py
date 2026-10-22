"""Self-check de la fecha del scraper de Cine Estudio. No toca la red ni la BD.
Uso: docker compose exec api python tests/check_cine_estudio.py"""
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.scrapers.cines.cine_estudio import parsear_fecha_hora
from app.services.tiempo import resolver_anio

assert parsear_fecha_hora("Dom 25/10, 17:00") == datetime(resolver_anio(10, 25), 10, 25, 17, 0)
assert parsear_fecha_hora("Lun 09/11, 19:00") == datetime(resolver_anio(11, 9), 11, 9, 19, 0)
for malo in ("", "Dom 25/10", "Dom 32/10, 17:00", "Dom 25/10, 25:00"):
    try:
        parsear_fecha_hora(malo)
        raise AssertionError(malo)
    except ValueError:
        pass
print("check_cine_estudio OK")
