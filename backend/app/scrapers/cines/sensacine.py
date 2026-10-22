"""Lee: el JSON de sesiones de SensaCine (https://www.sensacine.com/_/showtimes/theater-<id>/d-AAAA-MM-DD/), un cine por id y día, ~60 días vista.
Extrae: por sesión título, año de producción, startsAt, versión (original_st, local, dubbed, dubbed_st + code del relay) y enlace de compra (admit-one para Verdi). No da sala ni precio.
Se rompe si: cambia la ruta o la forma del JSON (results, showtimes, pagination) o un id de cine; si falla un cine se siguen los demás y al final se lanza la excepción."""
from sqlmodel import Session

from app.database.engine import engine
from app.scrapers.comun import FuenteNoDisponible, obtener_logger
from app.scrapers.plataforma_sensacine import leer_cine
from app.services.gestor_peliculas import resolver_pelicula
from app.services.pases import registrar_pase

IDS = {
    "Cines Verdi": "E0609",
    "Cines Callao": "E0146",
    "Artistic Metropol": "E0792",
    "Sala Berlanga": "E0736",
    "Pequeño Cine Estudio": "E0566",
    "Conde Duque Auditorio Morasol": "E0864",
}
CINES = list(IDS)
PRECIO = "Consultar"

log = obtener_logger(__name__)


def _scrapear_cine(session, cine, contadores):
    sesiones = leer_cine(IDS[cine], contadores)
    if not sesiones:
        log.warning("%s: SensaCine no da sesiones en los próximos días", cine)
    peliculas = {}  # (título, año) -> (pelicula_id, es_especial): una llamada a resolver_pelicula por película
    for s in sesiones:
        clave = (s.titulo, s.anio)
        if clave not in peliculas:
            peliculas[clave] = resolver_pelicula(session, s.titulo, cine, anio_web=s.anio)
        pelicula_id, es_especial = peliculas[clave]
        if pelicula_id is None:
            contadores["descartado"] += 1
            continue
        resultado = registrar_pase(
            session,
            cine=cine,
            pelicula_id=pelicula_id,
            fecha_hora=s.fecha_hora,
            sala=cine,  # SensaCine no da sala
            idioma=s.idioma,
            precio=PRECIO,
            link_compra=s.link,
            es_evento_especial=es_especial,
        )
        contadores[resultado] += 1


def scrapear_sensacine():
    fallos = {}

    with Session(engine) as session:
        for cine in CINES:
            contadores = {"creado": 0, "actualizado": 0, "descartado": 0, "sin_titulo": 0, "peticiones": 0}
            try:
                _scrapear_cine(session, cine, contadores)
            except FuenteNoDisponible as e:
                log.error("%s: el cine falla; se sigue con los demás", cine, exc_info=True)
                fallos[cine] = e
            log.info("%s: %s", cine, contadores)
        session.commit()

    # Se lanza después del commit: lo leído queda guardado y ejecutar_scraper no desactiva nada
    if fallos:
        raise FuenteNoDisponible(f"SensaCine: fallan {', '.join(fallos)}") from next(iter(fallos.values()))


if __name__ == "__main__":
    scrapear_sensacine()
