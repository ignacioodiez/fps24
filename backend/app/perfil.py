"""Perfil: nombre de usuario único y visibilidad (privado por defecto). Lo edita solo su dueño (user_id del token);
GET /u/{usuario} es público y solo enseña usuario, bio y, si el dueño lo activa, su diario; con el mismo 404 para un
perfil privado y uno inexistente. Nunca devuelve user_id, email ni ids de las entradas."""
import re
import time
from collections import defaultdict, deque
from datetime import date, datetime
from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import selectinload
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, SQLModel, select

from app.auth import Usuario, usuario_actual
from app.database.engine import get_session
from app.database.models import DiarioEntrada, Perfil
from app.diario import CineDiario, PeliculaDiario, _uid

router = APIRouter()

BIO_MAX = 160
POR_PAGINA = 30  # entradas del diario por página en el perfil público
USUARIO_MIN, USUARIO_MAX = 3, 20
# Rutas del sitio, cargos y palabras que se confunden con valores vacíos
RESERVADOS = frozenset("""
    admin administrador administradora administrator root superuser sistema system staff equipo moderador moderadora
    fps24 fps24es fps oficial soporte ayuda help contacto info hola email mail correo noreply no.reply www web
    api me yo perfil perfiles u usuario usuarios user users cuenta ajustes configuracion settings
    cine cines estrenos especiales pelicula peliculas diario cartelera buscar busqueda mapa sesiones pases
    login logout entrar salir registro signup signin auth privacidad legal terminos cookies sitemap robots favicon
    null undefined none nil nan true false anonimo anonymous test prueba
""".split())

PERFIL_INEXISTENTE = HTTPException(status_code=404, detail="Este perfil no existe o es privado")


def validar_usuario(texto: str) -> tuple:
    """Nombre de usuario -> (en minúsculas, motivo del rechazo o None). La única fuente de las reglas."""
    usuario = (texto or "").strip().lower()
    if not USUARIO_MIN <= len(usuario) <= USUARIO_MAX:
        return usuario, f"El nombre de usuario debe tener entre {USUARIO_MIN} y {USUARIO_MAX} caracteres"
    if not re.fullmatch(r"[a-z0-9._]+", usuario):
        return usuario, "Solo puede tener letras sin tildes (a-z), números, punto y guion bajo"
    if usuario[0] in "._" or usuario[-1] in "._":
        return usuario, "No puede empezar ni acabar en punto o guion bajo"
    if ".." in usuario:
        return usuario, "No puede tener dos puntos seguidos"
    if usuario in RESERVADOS:
        return usuario, "Ese nombre de usuario está reservado"
    return usuario, None


class PerfilGuardar(SQLModel):
    usuario: str
    bio: Optional[str] = None
    visibilidad: Literal["privado", "publico"] = "privado"
    diario_publico: bool = False


class PerfilSalida(SQLModel):
    usuario: Optional[str] = None  # None: aún no lo ha creado
    bio: Optional[str] = None
    visibilidad: str = "privado"
    diario_publico: bool = False
    creado_en: Optional[datetime] = None
    actualizado_en: Optional[datetime] = None


class EntradaPublica(SQLModel):
    pelicula: PeliculaDiario
    cine: Optional[CineDiario] = None
    fecha_vista: date
    nota: Optional[int] = None
    comentario: Optional[str] = None


class DiarioPublico(SQLModel):
    total: int
    pagina: int
    por_pagina: int
    entradas: List[EntradaPublica]


class PerfilPublico(SQLModel):
    usuario: str
    bio: Optional[str] = None
    diario_publico: bool = False
    diario: Optional[DiarioPublico] = None  # solo si el perfil es público y diario_publico


class Disponible(SQLModel):
    disponible: bool
    motivo: Optional[str] = None


# shortcut: límite en memoria por proceso (se reinicia con la API y se multiplica por nº de workers); si hay
# varias instancias, pasarlo a la BD o a Redis
LIMITE_DISPONIBLE, VENTANA_S = 30, 60
_consultas = defaultdict(deque)  # user_id -> instantes de sus últimas consultas


def _limitar(user_id: str):
    ahora, consultas = time.monotonic(), _consultas[user_id]
    while consultas and ahora - consultas[0] > VENTANA_S:
        consultas.popleft()
    if len(consultas) >= LIMITE_DISPONIBLE:
        raise HTTPException(status_code=429, detail="Demasiadas comprobaciones seguidas. Espera un minuto.")
    consultas.append(ahora)


def _por_nombre(session: Session, usuario: str) -> Optional[Perfil]:
    return session.exec(select(Perfil).where(func.lower(Perfil.usuario) == usuario.lower())).first()


@router.get("/me/perfil", response_model=PerfilSalida)
def leer_mi_perfil(usuario: Usuario = Depends(usuario_actual), session: Session = Depends(get_session)):
    perfil = session.get(Perfil, _uid(usuario))
    return PerfilSalida.model_validate(perfil) if perfil else PerfilSalida()


@router.put("/me/perfil", response_model=PerfilSalida)
def guardar_mi_perfil(datos: PerfilGuardar, usuario: Usuario = Depends(usuario_actual),
                      session: Session = Depends(get_session)):
    nombre, motivo = validar_usuario(datos.usuario)
    if motivo:
        raise HTTPException(status_code=422, detail=motivo)
    bio = (datos.bio or "").strip() or None
    if bio and len(bio) > BIO_MAX:
        raise HTTPException(status_code=422, detail=f"La bio no puede pasar de {BIO_MAX} caracteres")
    valores = dict(usuario=nombre, bio=bio, visibilidad=datos.visibilidad, diario_publico=datos.diario_publico)
    # Un solo INSERT ... ON CONFLICT: sin SELECT previo, dos peticiones a la vez no pueden duplicar el perfil ni
    # el nombre (lo garantizan la clave primaria y uq_perfil_usuario)
    consulta = (insert(Perfil).values(user_id=_uid(usuario), **valores)
                .on_conflict_do_update(index_elements=["user_id"], set_=dict(valores, actualizado_en=func.now())))
    try:
        session.exec(consulta)
        session.commit()
    except IntegrityError as e:
        session.rollback()
        if "uq_perfil_usuario" in str(e.orig):
            raise HTTPException(status_code=409, detail="Ese nombre de usuario ya está en uso")
        raise
    return PerfilSalida.model_validate(session.get(Perfil, _uid(usuario)))


@router.get("/usuarios/disponible", response_model=Disponible)
def usuario_disponible(u: str = Query(""), usuario: Usuario = Depends(usuario_actual),
                       session: Session = Depends(get_session)):
    _limitar(usuario.id)
    nombre, motivo = validar_usuario(u)
    if motivo:
        return Disponible(disponible=False, motivo=motivo)
    dueno = _por_nombre(session, nombre)
    if dueno and dueno.user_id != _uid(usuario):
        return Disponible(disponible=False, motivo="Ese nombre de usuario ya está en uso")
    return Disponible(disponible=True)


# Público. Mismo 404 (y mismo cuerpo) si no existe, es privado o el nombre ni siquiera es válido.
@router.get("/u/{usuario}", response_model=PerfilPublico)
def leer_perfil_publico(usuario: str, pagina: int = Query(1, ge=1, le=10_000), session: Session = Depends(get_session)):
    perfil = _por_nombre(session, usuario) if len(usuario) <= USUARIO_MAX else None
    if perfil is None or perfil.visibilidad != "publico":
        raise PERFIL_INEXISTENTE
    salida = PerfilPublico(usuario=perfil.usuario, bio=perfil.bio, diario_publico=perfil.diario_publico)
    if perfil.diario_publico:  # y es público: un perfil privado nunca llega aquí
        suyas = DiarioEntrada.user_id == perfil.user_id
        total = session.exec(select(func.count()).select_from(DiarioEntrada).where(suyas)).one()
        entradas = session.exec(
            select(DiarioEntrada).options(selectinload(DiarioEntrada.pelicula), selectinload(DiarioEntrada.cine))
            .where(suyas)
            .order_by(DiarioEntrada.fecha_vista.desc(), DiarioEntrada.creado_en.desc(), DiarioEntrada.id.desc())
            .offset((pagina - 1) * POR_PAGINA).limit(POR_PAGINA)
        ).all()
        salida.diario = DiarioPublico(total=total, pagina=pagina, por_pagina=POR_PAGINA,
                                      entradas=[EntradaPublica.model_validate(e) for e in entradas])
    return salida
