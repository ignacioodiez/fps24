from datetime import datetime, timezone

from sqlalchemy import func
from sqlmodel import Session, select

from app.database.models import Pase
from app.services.cines import obtener_o_crear_cine


def registrar_pase(session: Session, *, cine, pelicula_id, fecha_hora, sala, idioma,
                   precio, link_compra, es_evento_especial) -> str:
    """Crea o actualiza el pase y devuelve "creado" o "actualizado". El commit lo hace quien llama."""
    cine_id = obtener_o_crear_cine(session, cine).id
    # La columna es timestamp sin zona: se guarda la hora UTC sin tzinfo.
    ahora = datetime.now(timezone.utc).replace(tzinfo=None)

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
