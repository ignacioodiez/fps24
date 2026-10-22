import logging
import re
import unicodedata

from sqlmodel import Session, select

from app.database.models import Cine

logger = logging.getLogger(__name__)

# Nombre canónico -> slug. Los scrapers pueden escribir el nombre con otra
# capitalización, tildes o espacios: se comparan normalizados.
CINES_CONOCIDOS = {
    "Cine MK2 Paz": "mk2-paz",
    "Cine Doré": "dore",
    "Cine Embajadores": "embajadores",
    "Cine Embajadores Río": "embajadores-rio",
    "Cine Estudio (CBA)": "cine-estudio",
    "Cines Verdi": "verdi",
    "Cines Callao": "callao",
    "Artistic Metropol": "artistic-metropol",
    "Sala Berlanga": "sala-berlanga",
    "Pequeño Cine Estudio": "pequeno-cine-estudio",
    "Conde Duque Auditorio Morasol": "conde-duque-morasol",
    "Cinesa Proyecciones": "cinesa-proyecciones",
    "Cinesa Príncipe Pío": "cinesa-principe-pio",
    "Cineteca": "cineteca",
    "Golem Madrid": "golem",
    "Mk2 Palacio de Hielo": "mk2-palacio-hielo",
    "Renoir Plaza de España": "renoir-plaza-espana",
    "Renoir Princesa": "renoir-princesa",
    "Renoir Retiro": "renoir-retiro",
    "Sala Equis": "equis",
    "Yelmo Cines Ideal": "yelmo-ideal",
}


def limpiar_espacios(nombre: str) -> str:
    return " ".join(nombre.split())


def normalizar(nombre: str) -> str:
    """Minúsculas, sin tildes y con los espacios repetidos colapsados."""
    sin_tildes = unicodedata.normalize("NFKD", nombre).encode("ascii", "ignore").decode()
    return limpiar_espacios(sin_tildes).lower()


def slugify(nombre: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", normalizar(nombre)).strip("-")


_POR_NOMBRE_NORMALIZADO = {normalizar(n): (n, s) for n, s in CINES_CONOCIDOS.items()}


def obtener_o_crear_cine(session: Session, nombre: str) -> Cine:
    """Devuelve el cine por slug y lo crea si no existe. El commit lo hace quien llama."""
    conocido = _POR_NOMBRE_NORMALIZADO.get(normalizar(nombre))
    if conocido:
        nombre_canonico, slug = conocido
    else:
        nombre_canonico, slug = limpiar_espacios(nombre), slugify(nombre)
        logger.warning("Cine desconocido %r: uso el slug %r", nombre, slug)

    cine = session.exec(select(Cine).where(Cine.slug == slug)).first()
    if cine is None:
        cine = Cine(slug=slug, nombre=nombre_canonico)
        session.add(cine)
        session.flush()
    return cine
