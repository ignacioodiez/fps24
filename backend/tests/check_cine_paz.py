"""Self-check de la plantilla mk2 (pestañas y horas) y del idioma de Cine Paz. No toca la red ni la BD.
Uso: docker compose exec api python tests/check_cine_paz.py"""
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.scrapers.cines.cine_paz import idioma_de
from app.scrapers.plataforma_mk2 import parsear_hora, parsear_rotulo
from app.services.tiempo import hoy_madrid, resolver_anio

assert parsear_rotulo("Hoy") == hoy_madrid()
assert parsear_rotulo(" Mañana ") == hoy_madrid() + timedelta(days=1)
assert parsear_rotulo("Sábado 24/10") == date(resolver_anio(10, 24), 10, 24)
assert parsear_rotulo("Lunes 02/11") == date(resolver_anio(11, 2), 11, 2)
for malo in ("", "Sábado", "Sábado 32/10"):
    try:
        parsear_rotulo(malo)
        raise AssertionError(malo)
    except ValueError:
        pass

assert parsear_hora("35mm15:45") == (15, 45)
assert parsear_hora("VOSE 22:30") == (22, 30)
for malo in ("", "15.45", "9:30"):
    try:
        parsear_hora(malo)
        raise AssertionError(malo)
    except ValueError:
        pass

assert idioma_de("Anora (VOSE)", False) == "VOSE"
assert idioma_de("Anora (v.o.s.e)", False) == "VOSE"
assert idioma_de("Anora", True) == "VOSE"
assert idioma_de("La bola negra (35mm)", False) == "Español"
print("check_cine_paz OK")
