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


# Ficha de cada cine, por slug: sincronizar_cines() la copia a la tabla cine al empezar lanzar_todo.
# tipo: "autor" o "comercial" (destacadas solo usa los especiales de cines de autor).
CINES_DATOS = {
    "dore": dict(direccion="Calle de Santa Isabel, 3, 28012 Madrid", web="https://www.cultura.gob.es/cultura/areas/cine/mc/fe/cine-dore.html",
                 telefono="91 369 32 25", zona="Lavapiés", tipo="autor", lat=40.4118385, lng=-3.6991286),
    "cine-estudio": dict(direccion="Calle del Marqués de Casa Riera, 4, 28014 Madrid", web="https://www.circulobellasartes.com/cine-estudio",
                         telefono="91 389 24 26", zona="Centro", tipo="autor", lat=40.4178989, lng=-3.696253),
    "verdi": dict(direccion="Calle de Bravo Murillo, 28, 28015 Madrid", web="http://www.cines-verdi.com/",
                  telefono="91 447 39 30", zona="Chamberí", tipo="autor", lat=40.4366289, lng=-3.704094),
    "pequeno-cine-estudio": dict(direccion="Calle de Magallanes, 1, 28015 Madrid", web="https://www.pcineestudio.es",
                                 telefono="91 447 29 20", zona="Chamberí", tipo="autor", lat=40.4324328, lng=-3.7058074),
    "sala-berlanga": dict(direccion="Calle de Andrés Mellado, 53, 28015 Madrid", web="http://www.salaberlanga.com",
                          telefono="91 455 08 78", zona="Chamberí", tipo="autor", lat=40.43594, lng=-3.7144902),
    "mk2-paz": dict(direccion="Calle de Fuencarral, 125, 28010 Madrid", web=None,
                    telefono="914 46 45 66", zona="Chamberí", tipo="autor", lat=40.430899, lng=-3.7034531),
    "cinesa-proyecciones": dict(direccion="Calle de Fuencarral, 136, 28010 Madrid", web="https://www.cinesa.es/cines/proyecciones",
                                telefono=None, zona="Chamberí", tipo="comercial", lat=40.4315549, lng=-3.7029393),
    "callao": dict(direccion="Plaza del Callao, 3, 28013 Madrid", web="https://cinescallao.es",
                   telefono="91 522 58 01", zona="Centro", tipo="comercial", lat=40.42011952719996, lng=-3.70616110470047),
    "golem": dict(direccion="Calle de Martín de los Heros, 14, 28008 Madrid", web="https://www.golem.es/golem/golem-madrid",
                  telefono="91 559 38 36", zona="Argüelles", tipo="autor", lat=40.4246171, lng=-3.7136082),
    "renoir-plaza-espana": dict(direccion="Calle de Martín de los Heros, 12, 28008 Madrid", web="https://www.cinesrenoir.com/cine/renoir-plaza-de-espana/cartelera",
                                telefono="91 334 21 77", zona="Argüelles", tipo="autor", lat=40.4244029, lng=-3.7134171),
    "renoir-princesa": dict(direccion="Calle de la Princesa, 3, 28008 Madrid", web="https://www.cinesrenoir.com/cine/cines-princesa/cartelera",
                            telefono="91 334 21 77", zona="Argüelles", tipo="autor", lat=40.4250418, lng=-3.7124448),
    "renoir-retiro": dict(direccion="Calle de Narváez, 38, 28009 Madrid", web="https://www.cinesrenoir.com",
                          telefono=None, zona="Retiro", tipo="autor", lat=40.4205434, lng=-3.6762506),
    "equis": dict(direccion="Calle del Duque de Alba, 4, 28012 Madrid", web="https://salaequis.es",
                  telefono=None, zona="Lavapiés", tipo="autor", lat=40.4120092, lng=-3.7059791),
    "embajadores": dict(direccion="Glorieta de Santa María de la Cabeza, 5, 28045 Madrid", web="https://cinesembajadores.es",
                        telefono="91 485 87 98", zona="Lavapiés", tipo="autor", lat=40.4006484, lng=-3.6984823),
    "embajadores-rio": dict(direccion="Calle de Ercilla, 53, 28045 Madrid", web="https://cinesembajadores.es",
                            telefono=None, zona="Lavapiés", tipo="autor", lat=40.4001242, lng=-3.7006198),
    "cineteca": dict(direccion="Plaza de Legazpi, 8, 28045 Madrid", web="http://www.cinetecamadrid.com",
                     telefono="91 318 46 74", zona="Arganzuela", tipo="autor", lat=40.3916842144335, lng=-3.696404072155813),
    "artistic-metropol": dict(direccion="Calle de las Cigarreras, 6, 28005 Madrid", web=None,
                              telefono="915 272 792", zona="Arganzuela", tipo="autor", lat=40.4049046, lng=-3.7074611),
    "yelmo-ideal": dict(direccion="Calle del Doctor Cortezo, 6, 28012 Madrid", web="https://yelmocines.es/cartelera/madrid/ideal",
                        telefono="902 22 09 22", zona="Centro", tipo="comercial", lat=40.4136608, lng=-3.7038863),
    "cinesa-principe-pio": dict(direccion="Paseo de la Florida, 2, 28008 Madrid", web=None,
                                telefono=None, zona="Moncloa", tipo="comercial", lat=40.4221458, lng=-3.7204964),
    "conde-duque-morasol": dict(direccion="Calle de Pradillo, 4, 28002 Madrid", web=None,
                                telefono="910 52 43 80", zona="Chamartín", tipo="comercial", lat=40.4482811, lng=-3.6759879),
    "mk2-palacio-hielo": dict(direccion="Centro Comercial Palacio de Hielo, Calle de Silvano, 77, 28043 Madrid", web=None,
                              telefono=None, zona="Hortaleza", tipo="comercial", lat=40.4630376, lng=-3.6376566),
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


def sincronizar_cines(session: Session) -> int:
    """Copia CINES_DATOS a la tabla cine: crea los que falten y rellena sus columnas, sin pisar un valor
    con None. No toca los cines que no estén en CINES_DATOS. Devuelve cuántos cambian. Flush, no commit."""
    nombres = {s: n for n, s in CINES_CONOCIDOS.items()}
    existentes = {c.slug: c for c in session.exec(select(Cine).where(Cine.slug.in_(list(CINES_DATOS)))).all()}
    cambiados = 0
    for slug, datos in CINES_DATOS.items():
        cine = existentes.get(slug) or Cine(slug=slug, nombre=nombres[slug])
        nuevos = {k: v for k, v in datos.items() if v is not None and getattr(cine, k) != v}
        if nuevos or cine.id is None:
            for campo, valor in nuevos.items():
                setattr(cine, campo, valor)
            session.add(cine)
            cambiados += 1
    session.flush()
    return cambiados
