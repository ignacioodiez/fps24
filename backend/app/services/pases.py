import logging
from datetime import datetime, timezone

from sqlalchemy import func, or_, update
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.database.engine import engine
from app.database.models import Cine, Pase
from app.services.cines import CINES_CONOCIDOS, normalizar, obtener_o_crear_cine
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

    # La misma identidad que el índice único ux_pase_identidad
    buscar = select(Pase).where(
        Pase.cine_id == cine_id,
        Pase.pelicula_id == pelicula_id,
        Pase.fecha_hora == fecha_hora,
        func.coalesce(Pase.idioma, "") == (idioma or ""),
        func.coalesce(Pase.sala, "") == (sala or ""),
    )
    pase = session.exec(buscar).first()

    resultado = "actualizado"
    if pase is None:
        try:
            with session.begin_nested():  # otra ejecución puede crear el mismo pase a la vez
                pase = Pase(cine_id=cine_id, pelicula_id=pelicula_id,
                            fecha_hora=fecha_hora, sala=sala, idioma=idioma)
                session.add(pase)
            resultado = "creado"
        except IntegrityError:
            pase = session.exec(buscar).one()

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


def ejecutar_scraper(funcion_scraper, cines=()) -> dict:
    """Ejecuta el scraper y cierra la ejecución. Si el scraper falla, no se cierra nada.
    Devuelve el resumen de cerrar_ejecucion por slug, con creados y actualizados. Avisa de los
    `cines` (nombres canónicos) que tenían pases activos futuros y esta vez no se han visto."""
    inicio = _ahora_utc()
    with Session(engine) as session:
        previos = contar_activos_futuros(session)
        ultimo_id = session.exec(select(func.max(Pase.id))).one() or 0
    funcion_scraper()
    with Session(engine) as session:
        resumen = cerrar_ejecucion(session, inicio, previos)
        session.commit()
        # Con el candado de lanzar_todo nadie más crea pases: los de id nuevo son de esta ejecución
        for cine in session.exec(select(Cine).where(Cine.slug.in_(resumen))):
            creados = session.exec(select(func.count()).where(Pase.cine_id == cine.id, Pase.id > ultimo_id)).one()
            resumen[cine.slug].update(creados=creados, actualizados=resumen[cine.slug]["vistos"] - creados)
        slugs = [CINES_CONOCIDOS.get(nombre) for nombre in cines]
        for cine in session.exec(select(Cine).where(Cine.slug.in_(slugs))):
            if previos.get(cine.id) and cine.slug not in resumen:
                logger.warning("%s: tenía %d pases futuros activos y esta ejecución no ha visto ninguno; "
                               "no se desactivan (¿ha cambiado la web?)", cine.nombre, previos[cine.id])
    print(f"Cierre de {funcion_scraper.__name__}: {resumen}")
    return resumen
