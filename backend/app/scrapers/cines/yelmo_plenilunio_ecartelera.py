"""Lee: la cartelera de Yelmo Plenilunio en eCartelera (https://www.ecartelera.com/cines/517,N,1.html; ver app/scrapers/plataforma_ecartelera.py).
Extrae: título y horas. Versión: siempre Español (IDIOMA).
Se rompe si: cambia la plantilla de eCartelera (ver la plataforma)."""
from app.scrapers.plataforma_ecartelera import scrapear

ID_ECARTELERA = 517
CINES = ["Yelmo Cines Plenilunio"]
SALA = "Yelmo Plenilunio"  # forma parte de la identidad del pase
LINK_COMPRA = "https://yelmocines.es/cartelera/madrid/plenilunio"
# Decisión del cine, no heurística: Yelmo Plenilunio no proyecta en VO (comprobado a mano el 24-10-2026).
# Si empieza a programar VOSE, quitar IDIOMA y pasar a la versión por país, como Yelmo Ideal.
IDIOMA = "Español"


def scrapear_yelmo_plenilunio_ecartelera():
    scrapear(ID_ECARTELERA, CINES[0], SALA, LINK_COMPRA, idioma_fijo=IDIOMA)


if __name__ == "__main__":
    scrapear_yelmo_plenilunio_ecartelera()
