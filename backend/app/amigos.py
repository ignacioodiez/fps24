"""Amigos: amistad mutua (solicitud + aceptación) y bloqueo. Todo del propio usuario (user_id del token) y por nombre
de usuario, nunca por user_id. Pedir amistad responde siempre lo mismo, exista o no la otra persona, sea uno mismo,
haya bloqueo o ya haya solicitud o amistad: el POST no sirve para averiguar quién existe ni quién te ha bloqueado."""
import uuid
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import and_, case, func, or_
from sqlalchemy.dialects.postgresql import insert
from sqlmodel import Session, SQLModel, delete, select, update

from app.auth import Usuario, usuario_actual
from app.database.engine import get_session
from app.database.models import Amistad, Bloqueo, Perfil
from app.diario import _uid
from app.perfil import USUARIO_MAX, Avatar, _avatar, _por_nombre
from app.services.tiempo import hoy_madrid

router = APIRouter()

MAX_PENDIENTES = 20  # enviadas sin respuesta a la vez
MAX_AL_DIA = 10  # solicitudes nuevas por día de Madrid; cuenta cada intento, para que el tope no delate quién existe
ENVIADA = {"mensaje": "Si existe, le hemos enviado la solicitud"}
SIN_PERFIL = HTTPException(status_code=422, detail="Elige antes tu nombre de usuario en «Editar mi perfil»")
NO_ENCONTRADA = HTTPException(status_code=404, detail="Solicitud no encontrada")


class PorUsuario(SQLModel):
    usuario: str


class Persona(SQLModel):
    usuario: str
    avatar: Avatar


class Solicitud(Persona):
    id: uuid.UUID  # opaco; solo sirve a su solicitante y a su destinatario
    creada_en: datetime


class MisAmigos(SQLModel):
    amigos: List[Persona]
    recibidas: List[Solicitud]
    enviadas: List[Solicitud]


def normalizar(texto: str) -> str:
    return (texto or "").strip().lower().removeprefix("@").strip()


def _mio(session: Session, usuario: Usuario) -> Perfil:
    """Mi perfil: sin él no hay amigos ni bloqueos (las tablas apuntan a perfil)."""
    perfil = session.get(Perfil, _uid(usuario))
    if perfil is None:
        raise SIN_PERFIL
    return perfil


def _otro(session: Session, texto: str):
    usuario = normalizar(texto)
    return _por_nombre(session, usuario) if usuario and len(usuario) <= USUARIO_MAX else None


def _entre(a, b):
    return or_(and_(Amistad.solicitante_id == a, Amistad.destinatario_id == b),
               and_(Amistad.solicitante_id == b, Amistad.destinatario_id == a))


def _hay_bloqueo(session: Session, a, b) -> bool:
    return session.exec(select(Bloqueo).where(or_(and_(Bloqueo.bloqueador_id == a, Bloqueo.bloqueado_id == b),
                                                  and_(Bloqueo.bloqueador_id == b, Bloqueo.bloqueado_id == a)))).first() is not None


@router.post("/me/amigos/solicitudes")
def pedir_amistad(datos: PorUsuario, usuario: Usuario = Depends(usuario_actual), session: Session = Depends(get_session)):
    yo = _mio(session, usuario)
    # Serializa por usuario el "contar y enviar" (como en sesiones.py) para que dos peticiones a la vez no pasen los topes
    session.exec(select(func.pg_advisory_xact_lock(func.hashtextextended(str(yo.user_id), 0))))
    session.refresh(yo)
    hoy = hoy_madrid()
    hechas = yo.solicitudes_hoy if yo.solicitudes_dia == hoy else 0
    if hechas >= MAX_AL_DIA:
        raise HTTPException(status_code=429, detail=f"Has llegado al máximo de {MAX_AL_DIA} solicitudes de amistad por día. Prueba mañana.")
    pendientes = session.exec(select(func.count()).where(Amistad.solicitante_id == yo.user_id, Amistad.estado == "pendiente")).one()
    if pendientes >= MAX_PENDIENTES:
        raise HTTPException(status_code=409, detail=f"Tienes {MAX_PENDIENTES} solicitudes sin respuesta. Cancela alguna para enviar más.")
    yo.solicitudes_dia, yo.solicitudes_hoy = hoy, hechas + 1
    session.add(yo)
    otro = _otro(session, datos.usuario)
    if otro and otro.user_id != yo.user_id and not _hay_bloqueo(session, yo.user_id, otro.user_id):
        previa = session.exec(select(Amistad).where(_entre(yo.user_id, otro.user_id))).first()
        if previa is None:
            # Si la otra persona la crea a la vez, gana una de las dos (uq_amistad_par) y no pasa nada
            session.exec(insert(Amistad).values(solicitante_id=yo.user_id, destinatario_id=otro.user_id).on_conflict_do_nothing())
        elif previa.estado == "pendiente" and previa.solicitante_id == otro.user_id:  # me la había pedido: aceptada
            session.exec(update(Amistad).where(Amistad.id == previa.id).values(estado="aceptada", respondida_en=func.now()))
    session.commit()
    return ENVIADA


@router.get("/me/amigos", response_model=MisAmigos)
def leer_amigos(usuario: Usuario = Depends(usuario_actual), session: Session = Depends(get_session)):
    uid = _uid(usuario)
    otro = case((Amistad.solicitante_id == uid, Amistad.destinatario_id), else_=Amistad.solicitante_id)
    filas = session.exec(select(Amistad, Perfil).join(Perfil, Perfil.user_id == otro)
                         .where(or_(Amistad.solicitante_id == uid, Amistad.destinatario_id == uid))
                         .order_by(Amistad.creada_en.desc())).all()
    salida = MisAmigos(amigos=[], recibidas=[], enviadas=[])
    for amistad, perfil in filas:
        persona = dict(usuario=perfil.usuario, avatar=_avatar(session, perfil))
        if amistad.estado == "aceptada":
            salida.amigos.append(Persona(**persona))
        else:
            lista = salida.enviadas if amistad.solicitante_id == uid else salida.recibidas
            lista.append(Solicitud(id=amistad.id, creada_en=amistad.creada_en, **persona))
    salida.amigos.sort(key=lambda p: p.usuario)
    return salida


@router.post("/me/amigos/solicitudes/{solicitud_id}/aceptar", status_code=204)
def aceptar(solicitud_id: uuid.UUID, usuario: Usuario = Depends(usuario_actual), session: Session = Depends(get_session)):
    hecho = session.exec(update(Amistad).where(Amistad.id == solicitud_id, Amistad.destinatario_id == _uid(usuario),
                                               Amistad.estado == "pendiente")
                         .values(estado="aceptada", respondida_en=func.now())).rowcount
    if not hecho:
        raise NO_ENCONTRADA
    session.commit()
    return Response(status_code=204)


@router.post("/me/amigos/solicitudes/{solicitud_id}/rechazar", status_code=204)
def rechazar(solicitud_id: uuid.UUID, usuario: Usuario = Depends(usuario_actual), session: Session = Depends(get_session)):
    """Borra la solicitud: quien la envió la ve desaparecer de sus enviadas, sin aviso."""
    hecho = session.exec(delete(Amistad).where(Amistad.id == solicitud_id, Amistad.destinatario_id == _uid(usuario),
                                               Amistad.estado == "pendiente")).rowcount
    if not hecho:
        raise NO_ENCONTRADA
    session.commit()
    return Response(status_code=204)


@router.delete("/me/amigos/solicitudes/{solicitud_id}", status_code=204)
def cancelar(solicitud_id: uuid.UUID, usuario: Usuario = Depends(usuario_actual), session: Session = Depends(get_session)):
    """Idempotente, como quitar una sesión guardada: si no es mía o ya no está, también 204."""
    session.exec(delete(Amistad).where(Amistad.id == solicitud_id, Amistad.solicitante_id == _uid(usuario),
                                       Amistad.estado == "pendiente"))
    session.commit()
    return Response(status_code=204)


@router.delete("/me/amigos/{usuario_amigo}", status_code=204)
def quitar_amigo(usuario_amigo: str, usuario: Usuario = Depends(usuario_actual), session: Session = Depends(get_session)):
    otro = _otro(session, usuario_amigo)
    if otro:
        session.exec(delete(Amistad).where(_entre(_uid(usuario), otro.user_id), Amistad.estado == "aceptada"))
        session.commit()
    return Response(status_code=204)


@router.get("/me/bloqueos", response_model=List[Persona])
def leer_bloqueos(usuario: Usuario = Depends(usuario_actual), session: Session = Depends(get_session)):
    perfiles = session.exec(select(Perfil).join(Bloqueo, Bloqueo.bloqueado_id == Perfil.user_id)
                            .where(Bloqueo.bloqueador_id == _uid(usuario)).order_by(Perfil.usuario)).all()
    return [Persona(usuario=p.usuario, avatar=_avatar(session, p)) for p in perfiles]


@router.post("/me/bloqueos", status_code=204)
def bloquear(datos: PorUsuario, usuario: Usuario = Depends(usuario_actual), session: Session = Depends(get_session)):
    """Siempre 204 (exista o no). Borra la amistad y las solicitudes en los dos sentidos."""
    yo = _mio(session, usuario)
    otro = _otro(session, datos.usuario)
    if otro and otro.user_id != yo.user_id:
        session.exec(insert(Bloqueo).values(bloqueador_id=yo.user_id, bloqueado_id=otro.user_id).on_conflict_do_nothing())
        session.exec(delete(Amistad).where(_entre(yo.user_id, otro.user_id)))
        session.commit()
    return Response(status_code=204)


@router.delete("/me/bloqueos/{usuario_bloqueado}", status_code=204)
def desbloquear(usuario_bloqueado: str, usuario: Usuario = Depends(usuario_actual), session: Session = Depends(get_session)):
    otro = _otro(session, usuario_bloqueado)
    if otro:
        session.exec(delete(Bloqueo).where(Bloqueo.bloqueador_id == _uid(usuario), Bloqueo.bloqueado_id == otro.user_id))
        session.commit()
    return Response(status_code=204)
