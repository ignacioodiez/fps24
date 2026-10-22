import logging
from datetime import datetime, timezone

from sqlalchemy import func, or_, update
from sqlmodel import Session, select

from app.database.engine import engine
from app.database.models import Cine, Pase
from app.services.cines import normalizar, obtener_o_crear_cine
from app.services.tiempo import ahora_madrid

logger = logging.getLogger(__name__)


def _ahora_utc():
    # La columna es timestamp sin zona: se guarda la hora UTC sin tzinfo.
    return datetime.now(timezone.utc).replace(tzinfo=None)


# Clave normalizada (minúsculas, sin tildes, puntos ni espacios) -> valor canónico.
IDIOMAS_CANONICOS = {"espanol": "Español", "vose": "VOSE"}


def normalizar_idioma(idioma):
    """Devuelve el valor canónico; si no lo conoce, avisa y lo deja tal cual."""
    clave = normalizar(idioma or "").replace(".", "").replace(" ", "")
    if clave in IDIOMAS_CANONICOS:
        return IDIOMAS_CANONICOS[clave]
    logger.warning("Idioma desconocido %r: se guarda tal cual", idioma)
    return idioma


def registrar_pase(session: Session, *, cine, pelicula_id, fecha_hora, sala, idioma,
                   precio, link_compra, es_evento_especial) -> str:
    """Crea o actualiza el pase y devuelve "creado" o "actualizado". El commit lo hace quien llama."""
    if pelicula_id is None:
        raise ValueError(f"Pase sin película en {cine} ({fecha_hora})")
    fecha_hora = fecha_hora.replace(microsecond=0)
    idioma = normalizar_idioma(idioma)
    cine_id = obtener_o_crear_cine(session, cine).id
    ahora = _ahora_utc()

    pase = session.exec(select(Pase).where(
        Pase.cine_id == cine_id,
        Pase.pelicula_id == pelicula_id,
        Pase.fecha_hora == fecha_hora,
        Pase.idioma == idioma,
        func.coalesce(Pase.sala, "") == (sala or ""),
    )).first()

    resultado = "actualizado"
    if pase is None:
        pase = Pase(cine=cine, cine_id=cine_id, pelicula_id=pelicula_id,
                    fecha_hora=fecha_hora, sala=sala, idioma=idioma)
        resultado = "creado"

    pase.precio = precio
    pase.link_compra = link_compra
    pase.es_evento_especial = es_evento_especial
    pase.activo = True
    pase.visto_ultima_vez = ahora
    session.add(pase)
    session.flush()
    return resultado


def contar_activos_futuros(session: Session) -> dict:
    """{cine_id: nº de pases activos con fecha_hora >= ahora en Madrid}."""
    return dict(session.exec(
        select(Pase.cine_id, func.count())
        .where(Pase.activo, Pase.fecha_hora >= ahora_madrid())
        .group_by(Pase.cine_id)
    ).all())


def cerrar_ejecucion(session: Session, inicio: datetime, activos_futuros_previos: dict) -> dict:
    """Desactiva los pases no vistos desde `inicio` (UTC sin tzinfo) en los cines tocados
    por la ejecución. El commit lo hace quien llama."""
    ahora = ahora_madrid()
    cine_ids = session.exec(
        select(Pase.cine_id).where(Pase.visto_ultima_vez >= inicio).distinct()
    ).all()

    resumen = {}
    for cine_id in cine_ids:
        cine = session.get(Cine, cine_id)
        vistos = session.exec(select(func.count()).where(
            Pase.cine_id == cine_id, Pase.visto_ultima_vez >= inicio)).one()
        vistos_futuros = session.exec(select(func.count()).where(
            Pase.cine_id == cine_id, Pase.visto_ultima_vez >= inicio,
            Pase.fecha_hora >= ahora)).one()
        previos = activos_futuros_previos.get(cine_id, 0)

        if vistos_futuros < previos / 2:
            logger.warning(
                "Salvaguarda en %s: vistos %d pases futuros de %d activos futuros previos. "
                "No se desactiva nada.", cine.nombre, vistos_futuros, previos)
            resumen[cine.slug] = dict(vistos=vistos, desactivados=0, saltado_por_salvaguarda=True)
            continue

        desactivados = session.exec(update(Pase).where(
            Pase.cine_id == cine_id, Pase.activo,
            or_(Pase.visto_ultima_vez < inicio, Pase.visto_ultima_vez.is_(None)),
        ).values(activo=False)).rowcount
        cine.ultima_ejecucion_ok = _ahora_utc()
        session.add(cine)
        resumen[cine.slug] = dict(vistos=vistos, desactivados=desactivados,
                                  saltado_por_salvaguarda=False)
    session.flush()
    return resumen


def ejecutar_scraper(funcion_scraper) -> dict:
    """Ejecuta el scraper y cierra la ejecución. Si el scraper falla, no se cierra nada."""
    inicio = _ahora_utc()
    with Session(engine) as session:
        previos = contar_activos_futuros(session)
    funcion_scraper()
    with Session(engine) as session:
        resumen = cerrar_ejecucion(session, inicio, previos)
        session.commit()
    print(f"Cierre de {funcion_scraper.__name__}: {resumen}")
    return resumen
