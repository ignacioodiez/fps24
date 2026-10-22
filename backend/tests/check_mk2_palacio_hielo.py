"""Self-check de la hora y el idioma de MK2 Palacio de Hielo. No toca la red ni la BD.
Uso: docker compose exec api python tests/check_mk2_palacio_hielo.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.scrapers.cines.mk2_palacio_hielo import idioma_de, parsear_hora

assert parsear_hora("19:00") == (19, 0)
assert parsear_hora("VOSE 9:30") == (9, 30)
for malo in ("", "Directo19:00", "TEATRO EN VIVO19:00", "VOSFR19:00", "19.00"):
    try:
        parsear_hora(malo)
        raise AssertionError(malo)
    except ValueError:
        pass
assert idioma_de("Anora (vose)", False) == "VOSE"
assert idioma_de("Anora", True) == "VOSE"
assert idioma_de("Anora VOSE", False) == "Español"  # sin paréntesis no cuenta, como antes
print("check_mk2_palacio_hielo OK")
