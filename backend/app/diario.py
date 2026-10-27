"""Diario: las películas que cada usuario ha visto en sala. Privado: toda consulta filtra por el user_id
del token (nunca por uno que mande el cliente) y una entrada ajena responde 404, como si no existiera."""
import uuid
from datetime import date, datetime, time, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import field_validator
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload
from sqlmodel import Field, Session, SQLModel, select

from app.auth import Usuario, no_autorizado, usuario_actual
from app.database.engine import get_session
from app.database.models import Cine, DiarioEntrada, Pase, Pelicula
from app.services.tiempo import hoy_madrid

router = APIRouter()

COMENTARIO_MAX = 2000


# --- Entrada ---

class _Validaciones(SQLModel):
    @field_validator("fecha_vista", "repeticion", check_fields=False)
    @classmethod
    def _no_nulo(cls, v, info):
        # Solo salta si el cliente manda null: los valores por defecto no se validan
        if v is None:
            raise ValueError(f"{info.field_name} no puede ser null")
        return v

    @field_validator("fecha_vista", check_fields=False)
    @classmethod
    def _no_futura(cls, v):
        if v > hoy_madrid():
            raise ValueError("fecha_vista no puede ser futura (hora de Madrid)")
        return v

    @field_validator("comentario", check_fields=False)
    @classmethod
    def _comentario(cls, v):
        v = (v or "").strip()
        if len(v) > COMENTARIO_MAX:
            raise ValueError(f"el comentario no puede pasar de {COMENTARIO_MAX} caracteres")
        return v or None


class EntradaCrear(_Validaciones):
    pelicula_id: int
    fecha_vista: date
    cine_slug: Optional[str] = None
    pase_id: Optional[int] = None
    nota: Optional[int] = Field(default=None, ge=1, le=10)  # 1-10 = ½ a 5 estrellas
    comentario: Optional[str] = None
    repeticion: bool = False


class EntradaEditar(_Validaciones):
    # Solo se tocan los campos que vengan; null en cine_slug, nota o comentario los borra
    fecha_vista: Optional[date] = None
    cine_slug: Optional[str] = None
    nota: Optional[int] = Field(default=None, ge=1, le=10)
    comentario: Optional[str] = None
    repeticion: Optional[bool] = None


# --- Salida ---

class PeliculaDiario(SQLModel):
    id: int
    titulo: str
    poster_url: Optional[str] = None
    anio: Optional[int] = None
    director: Optional[str] = None
    nota_tmdb: Optional[float] = None


class CineDiario(SQLModel):
    slug: str
    nombre: str


class EntradaSalida(SQLModel):
    id: int
    pelicula: PeliculaDiario
    cine: Optional[CineDiario] = None
    pase_id: Optional[int] = None
    fecha_vista: date
    nota: Optional[int] = None
    comentario: Optional[str] = None
    repeticion: bool
    creado_en: datetime
    actualizado_en: datetime


class ListaDiario(SQLModel):
    total: int
    este_anio: int = 0  # entradas con fecha_vista en el año en curso (Madrid), para las cifras de mi perfil
    entradas: List[EntradaSalida]


class CineDelDia(SQLModel):
    slug: str
    nombre: str
    horas: List[str]  # "HH:MM", en orden


# --- Ayudas ---

def _uid(usuario: Usuario) -> uuid.UUID:
    try:
        return uuid.UUID(usuario.id)
    except ValueError:
        raise no_autorizado("Token no válido")


def _mia(session: Session, uid: uuid.UUID, entrada_id: int) -> DiarioEntrada:
    entrada = session.exec(select(DiarioEntrada).where(DiarioEntrada.id == entrada_id, DiarioEntrada.user_id == uid)).first()
    if entrada is None:
        raise HTTPException(status_code=404, detail="Entrada no encontrada")
    return entrada


def _cine_id(session: Session, slug: Optional[str]) -> Optional[int]:
    if slug is None:
        return None
    cine = session.exec(select(Cine).where(Cine.slug == slug)).first()
    if cine is None:
        raise HTTPException(status_code=422, detail=f"Cine desconocido: {slug}")
    return cine.id


def cifras(session: Session, uid: uuid.UUID) -> tuple:
    """(total de entradas, entradas de este año en Madrid) de un usuario, en una sola consulta."""
    enero = date(hoy_madrid().year, 1, 1)
    return tuple(session.exec(
        select(func.count(), func.count().filter(DiarioEntrada.fecha_vista >= enero)).where(DiarioEntrada.user_id == uid)
    ).one())


def _guardar(session: Session, entrada: DiarioEntrada) -> EntradaSalida:
    session.add(entrada)
    try:
        session.commit()
    except IntegrityError as e:
        session.rollback()
        if "uq_diario_entrada_usuario_pelicula_fecha" in str(e.orig):
            raise HTTPException(status_code=409, detail="Ya tienes esta película en tu diario ese mismo día")
        raise
    session.refresh(entrada)
    # Se serializa aquí, con la sesión abierta (pelicula y cine se cargan al acceder)
    return EntradaSalida.model_validate(entrada)


# --- Endpoints ---

@router.get("/diario", response_model=ListaDiario)
def leer_diario(limite: int = Query(50, ge=1, le=200), desplazamiento: int = Query(0, ge=0),
                usuario: Usuario = Depends(usuario_actual), session: Session = Depends(get_session)):
    mias = DiarioEntrada.user_id == _uid(usuario)
    total, este_anio = cifras(session, _uid(usuario))
    entradas = session.exec(
        select(DiarioEntrada).options(selectinload(DiarioEntrada.pelicula), selectinload(DiarioEntrada.cine))
        .where(mias)
        .order_by(DiarioEntrada.fecha_vista.desc(), DiarioEntrada.creado_en.desc(), DiarioEntrada.id.desc())
        .offset(desplazamiento).limit(limite)
    ).all()
    return ListaDiario(total=total, este_anio=este_anio, entradas=[EntradaSalida.model_validate(e) for e in entradas])


@router.get("/diario/pelicula/{pelicula_id}", response_model=List[EntradaSalida])
def leer_diario_pelicula(pelicula_id: int, usuario: Usuario = Depends(usuario_actual),
                         session: Session = Depends(get_session)):
    entradas = session.exec(
        select(DiarioEntrada).options(selectinload(DiarioEntrada.pelicula), selectinload(DiarioEntrada.cine))
        .where(DiarioEntrada.user_id == _uid(usuario), DiarioEntrada.pelicula_id == pelicula_id)
        .order_by(DiarioEntrada.fecha_vista.desc(), DiarioEntrada.id.desc())
    ).all()
    return [EntradaSalida.model_validate(e) for e in entradas]


@router.post("/diario", response_model=EntradaSalida, status_code=201)
def crear_entrada(datos: EntradaCrear, usuario: Usuario = Depends(usuario_actual),
                  session: Session = Depends(get_session)):
    uid = _uid(usuario)
    if session.get(Pelicula, datos.pelicula_id) is None:
        raise HTTPException(status_code=422, detail="Película no encontrada")
    cine_id = _cine_id(session, datos.cine_slug)
    if datos.pase_id is not None:
        # El pase fija el cine: tiene que ser de esa película, ese día y (si viene) ese cine
        pase = session.get(Pase, datos.pase_id)
        if (pase is None or pase.pelicula_id != datos.pelicula_id or pase.fecha_hora.date() != datos.fecha_vista
                or cine_id not in (None, pase.cine_id)):
            raise HTTPException(status_code=422, detail="El pase no corresponde a esa película, fecha y cine")
        cine_id = pase.cine_id
    entrada = DiarioEntrada(user_id=uid, cine_id=cine_id,
                            **datos.model_dump(include={"pelicula_id", "fecha_vista", "pase_id", "nota", "comentario", "repeticion"}))
    return _guardar(session, entrada)


@router.patch("/diario/{entrada_id}", response_model=EntradaSalida)
def editar_entrada(entrada_id: int, datos: EntradaEditar, usuario: Usuario = Depends(usuario_actual),
                   session: Session = Depends(get_session)):
    entrada = _mia(session, _uid(usuario), entrada_id)
    cambios = datos.model_dump(exclude_unset=True)
    if "cine_slug" in cambios:
        cambios["cine_id"] = _cine_id(session, cambios.pop("cine_slug"))
    # Otro día u otro cine: el pase guardado ya no es el de esa entrada
    if any(k in cambios and cambios[k] != getattr(entrada, k) for k in ("fecha_vista", "cine_id")):
        entrada.pase_id = None
    for campo, valor in cambios.items():
        setattr(entrada, campo, valor)
    entrada.actualizado_en = func.now()
    return _guardar(session, entrada)


@router.delete("/diario/{entrada_id}", status_code=204)
def borrar_entrada(entrada_id: int, usuario: Usuario = Depends(usuario_actual),
                   session: Session = Depends(get_session)):
    session.delete(_mia(session, _uid(usuario), entrada_id))
    session.commit()
    return Response(status_code=204)


# Público: para elegir el cine al apuntar una película en el diario. Incluye pases inactivos y pasados.
@router.get("/pelicula/{pelicula_id}/cines", response_model=List[CineDelDia])
def leer_cines_del_dia(pelicula_id: int, fecha: date, session: Session = Depends(get_session)):
    if session.get(Pelicula, pelicula_id) is None:
        raise HTTPException(status_code=404, detail="Película no encontrada")
    dia = datetime.combine(fecha, time())
    pases = session.exec(
        select(Pase).options(selectinload(Pase.cine_rel))
        .where(Pase.pelicula_id == pelicula_id, Pase.fecha_hora >= dia, Pase.fecha_hora < dia + timedelta(days=1))
        .order_by(Pase.fecha_hora, Pase.id)
    ).all()
    cines = {}  # orden de inserción = primer pase del día
    for p in pases:
        cine = cines.setdefault(p.cine_id, dict(slug=p.cine_rel.slug, nombre=p.cine_rel.nombre, horas=[]))
        hora = p.fecha_hora.strftime("%H:%M")
        if hora not in cine["horas"]:  # mismo pase en VOSE y doblado, o en dos salas
            cine["horas"].append(hora)
    return list(cines.values())
