"""Lee: la cartelera de Yelmo Ideal en eCartelera (https://www.ecartelera.com/cines/54,N,1.html; ver app/scrapers/plataforma_ecartelera.py).
Extrae: título, país y horas. Versión: VOSE salvo producción española o latinoamericana (como hace Yelmo Ideal).
Se rompe si: cambia la plantilla de eCartelera (ver la plataforma)."""
from app.scrapers.plataforma_ecartelera import scrapear

ID_ECARTELERA = 54
CINES = ["Yelmo Cines Ideal"]
SALA = "Yelmo Ideal"  # la misma que el scraper de yelmocines.es: forma parte de la identidad del pase
LINK_COMPRA = "https://yelmocines.es/cartelera/madrid/ideal"


def scrapear_yelmo_ideal_ecartelera():
    scrapear(ID_ECARTELERA, CINES[0], SALA, LINK_COMPRA)


if __name__ == "__main__":
    scrapear_yelmo_ideal_ecartelera()
