"""Sesiones guardadas ("Mis sesiones"): la agenda privada de cada usuario. Privado como el diario: toda consulta filtra
por el user_id del token y una guardada ajena responde 404. Al guardar se copia la sesión desde la BD (nunca lo que
mande el cliente), para que la agenda siga entera aunque el scraper retire o borre el pase."""
from datetime import date, datetime, time
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import selectinload
from sqlmodel import Session, SQLModel, delete, select

from app.auth import Usuario, usuario_actual
from app.database.engine import get_session
from app.database.models import DiarioEntrada, Pase, SesionGuardada
from app.diario import _uid
from app.services.tiempo import ahora_madrid, hoy_madrid

router = APIRouter()

TOPE = 200  # guardadas por usuario, pasadas incluidas


class Guardar(SQLModel):
    sesion_id: int  # id del pase (el mismo "id" que traen /pases, /pelicula/{id} y /cines/{slug})


class GuardadaSalida(SQLModel):
    id: int
    sesion_id: Optional[int] = None  # None si el pase ya no existe: la copia sigue valiendo
    pelicula_id: Optional[int] = None
    titulo: str
    poster_url: Optional[str] = None
    cine_nombre: str
    cine_slug: str
    fecha: date
    hora: time
    idioma: Optional[str] = None
    link_compra: Optional[str] = None
    diario_entrada_id: Optional[int] = None
    creada_en: datetime


class Agenda(SQLModel):
    proximas: List[GuardadaSalida]
    pasadas: List[GuardadaSalida]


class Marca(SQLModel):
    id: int  # de la guardada, para quitarla desde el modal
    sesion_id: int


def _salida(g: SesionGuardada) -> GuardadaSalida:
    return GuardadaSalida(sesion_id=g.pase_id, **g.model_dump(exclude={"user_id", "pase_id", "cine_id"}))


def _mia(session: Session, uid, guardada_id: int, bloquear: bool = False) -> SesionGuardada:
    consulta = select(SesionGuardada).where(SesionGuardada.id == guardada_id, SesionGuardada.user_id == uid)
    guardada = session.exec(consulta.with_for_update() if bloquear else consulta).first()
    if guardada is None:
        raise HTTPException(status_code=404, detail="Sesión guardada no encontrada")
    return guardada


def _futura(g: SesionGuardada, ahora: datetime) -> bool:
    return datetime.combine(g.fecha, g.hora) >= ahora


@router.get("/me/sesiones", response_model=Agenda)
def leer_sesiones(usuario: Usuario = Depends(usuario_actual), session: Session = Depends(get_session)):
    """Próximas (desde ahora en Madrid, de la más cercana a la más lejana) y pasadas (de la más reciente atrás)."""
    todas = session.exec(select(SesionGuardada).where(SesionGuardada.user_id == _uid(usuario))
                         .order_by(SesionGuardada.fecha, SesionGuardada.hora, SesionGuardada.id)).all()
    ahora = ahora_madrid()
    return Agenda(proximas=[_salida(g) for g in todas if _futura(g, ahora)],
                  pasadas=[_salida(g) for g in reversed(todas) if not _futura(g, ahora)])


@router.get("/me/sesiones/ids", response_model=List[Marca])
def leer_ids(usuario: Usuario = Depends(usuario_actual), session: Session = Depends(get_session)):
    """Las guardadas de hoy en adelante cuyo pase sigue existiendo: con ellas la cartelera marca "Guardada"."""
    filas = session.exec(select(SesionGuardada.id, SesionGuardada.pase_id)
                         .where(SesionGuardada.user_id == _uid(usuario), SesionGuardada.fecha >= hoy_madrid(),
                                SesionGuardada.pase_id.is_not(None))).all()
    return [Marca(id=i, sesion_id=p) for i, p in filas]


@router.post("/me/sesiones", response_model=GuardadaSalida)
def guardar_sesion(datos: Guardar, usuario: Usuario = Depends(usuario_actual), session: Session = Depends(get_session)):
    """Idempotente: si ya estaba guardada, devuelve la que había (también con el tope lleno)."""
    uid = _uid(usuario)
    pase = session.exec(select(Pase).options(selectinload(Pase.pelicula), selectinload(Pase.cine_rel))
                        .where(Pase.id == datos.sesion_id, Pase.activo)).first()
    if pase is None or pase.pelicula is None:  # inactivas tampoco: ya no están en la cartelera
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    clave = dict(cine_nombre=pase.cine_rel.nombre, fecha=pase.fecha_hora.date(),
                 hora=pase.fecha_hora.time().replace(microsecond=0), titulo=pase.pelicula.titulo)
    # Serializa por usuario el "contar y guardar" para que dos peticiones a la vez no pasen del tope
    session.exec(select(func.pg_advisory_xact_lock(func.hashtextextended(str(uid), 0))))
    mias = SesionGuardada.user_id == uid
    ya = session.exec(select(SesionGuardada).where(mias, *(getattr(SesionGuardada, k) == v for k, v in clave.items()))).first()
    if ya is None:
        if session.exec(select(func.count()).where(mias)).one() >= TOPE:
            raise HTTPException(status_code=409, detail=f"Has llegado al máximo de {TOPE} sesiones guardadas. Quita alguna para guardar más.")
        ya = SesionGuardada(user_id=uid, pase_id=pase.id, pelicula_id=pase.pelicula_id, poster_url=pase.pelicula.poster_url,
                            cine_id=pase.cine_id, cine_slug=pase.cine_rel.slug, idioma=pase.idioma,
                            link_compra=pase.link_compra, **clave)
        session.add(ya)
    session.commit()  # suelta el lock
    session.refresh(ya)
    return _salida(ya)


@router.delete("/me/sesiones/{guardada_id}", status_code=204)
def quitar_sesion(guardada_id: int, usuario: Usuario = Depends(usuario_actual), session: Session = Depends(get_session)):
    """Idempotente, como quitar un cine favorito: si no estaba (o es de otro), también 204 y no toca nada."""
    session.exec(delete(SesionGuardada).where(SesionGuardada.id == guardada_id, SesionGuardada.user_id == _uid(usuario)))
    session.commit()
    return Response(status_code=204)


@router.post("/me/sesiones/{guardada_id}/vista", response_model=GuardadaSalida)
def marcar_vista(guardada_id: int, usuario: Usuario = Depends(usuario_actual), session: Session = Depends(get_session)):
    """"La vi": entrada de diario con esa película, día y cine. Idempotente; si ya había una entrada de esa película
    ese día (apuntada a mano), se enlaza esa en vez de crear otra."""
    uid = _uid(usuario)
    guardada = _mia(session, uid, guardada_id, bloquear=True)
    if guardada.pelicula_id is None:
        raise HTTPException(status_code=422, detail="Esta sesión ya no está unida a ninguna película: no se puede apuntar en el diario")
    if _futura(guardada, ahora_madrid()):
        raise HTTPException(status_code=422, detail="Esta sesión todavía no ha empezado")
    if guardada.diario_entrada_id is None:
        session.exec(insert(DiarioEntrada).values(
            user_id=uid, pelicula_id=guardada.pelicula_id, fecha_vista=guardada.fecha, cine_id=guardada.cine_id,
            pase_id=guardada.pase_id).on_conflict_do_nothing(constraint="uq_diario_entrada_usuario_pelicula_fecha"))
        guardada.diario_entrada_id = session.exec(select(DiarioEntrada.id).where(
            DiarioEntrada.user_id == uid, DiarioEntrada.pelicula_id == guardada.pelicula_id,
            DiarioEntrada.fecha_vista == guardada.fecha)).one()
        session.add(guardada)
        session.commit()
        session.refresh(guardada)
    return _salida(guardada)
