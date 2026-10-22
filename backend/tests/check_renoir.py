"""Self-check del idioma y la sala del scraper de Renoir. No toca la red ni la BD.
Uso: docker compose exec api python tests/check_renoir.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.scrapers.cines.renoir import CINES, SLUGS, idioma_de, sala_de

assert set(SLUGS) == set(CINES)
assert idioma_de(["de Jonatan Etzler", "Versión Original subtitulada a Castellano"]) == "VOSE"
assert idioma_de(["Versión Original Castellano"]) == "Español"
assert idioma_de([]) == "Español"

assert sala_de("sala 01", "Renoir Retiro") == "Renoir Retiro (Sala 01)"
assert sala_de("Sala 11 ", "Renoir Princesa") == "Renoir Princesa (Sala 11)"
assert sala_de("20:15", "Renoir Retiro") == "Renoir Retiro"
assert sala_de(None, "Renoir Retiro") == "Renoir Retiro"
print("check_renoir OK")
