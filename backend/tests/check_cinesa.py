"""Self-check de sala e idioma del scraper de Cinesa. No toca la red ni la BD.
Uso: docker compose exec api python tests/check_cinesa.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.scrapers.cines.cinesa import CINES, FA_IDS, idioma_de, sala_de

assert sala_de("Sala 3 XL") == "3 XL"
assert sala_de("Sala 2 iSense") == "2 iSense"
assert sala_de("") is None and sala_de(None) is None
assert idioma_de("Dune: Parte Tres (VOSE)") == "VOSE"
assert idioma_de("Dune: Parte Tres") == "Español"
assert set(FA_IDS) == set(CINES)
print("check_cinesa OK")
