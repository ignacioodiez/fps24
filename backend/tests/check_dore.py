"""Self-check de los parsers de fecha y sala del scraper de Doré. No toca la red ni la BD.
Uso: docker compose exec api python tests/check_dore.py"""
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.scrapers.cines.dore import parsear_fecha, parsear_sala
from app.services.tiempo import resolver_anio

assert parsear_sala("a las 17:30h (Sala 1. PRESENTACIÓN LIBRO)") == "Sala 1"
assert parsear_sala("a las 19:00h\n( SALA  2 . CICLO)") == "Sala 2"
assert parsear_sala("a las 19:00h (sala2)") == "Sala 2"
assert parsear_sala("a las 19:00h (CICLO SIN SALA)") is None
assert parsear_sala("PRECIOS REDUCIDOS * Estudiantes") is None

d = parsear_fecha("Fecha y Hora: Jueves 22 de octubre a las 17:30h\n(Sala 1. CICLO)")
assert d == datetime(resolver_anio(10, 22), 10, 22, 17, 30), d
assert parsear_fecha("Sábado 3 de Enero   a las 9:05h 20:00").hour == 20  # la hora exige 2 dígitos
for malo in ("Sin fecha", "22 de brumario a las 17:30h"):
    try:
        parsear_fecha(malo)
        raise AssertionError(malo)
    except ValueError:
        pass
print("check_dore OK")
