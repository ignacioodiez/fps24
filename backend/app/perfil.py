"""Perfil: nombre de usuario único y visibilidad (privado por defecto). Lo edita solo su dueño (user_id del token);
GET /u/{usuario} es público y solo enseña usuario, bio, avatar, Letterboxd y, si el dueño los activa, su diario y sus
cines favoritos; con el mismo 404 para un perfil privado y uno inexistente. Nunca devuelve user_id, email ni ids de las
entradas."""
import re
import time
import zlib
from collections import defaultdict, deque
from datetime import date, datetime
from typing import Dict, List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import selectinload
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, SQLModel, select

from app.auth import Usuario, usuario_actual
from app.database.engine import get_session
from app.database.models import Cine, CineFavorito, DiarioEntrada, Pelicula, Perfil
from app.diario import CineDiario, PeliculaDiario, _uid, cifras

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

# Colores del avatar de iniciales: la única lista (el front la recibe en GET /me/perfil). Todos con contraste >= 4.5:1
# con texto blanco (lo comprueba tests/check_perfil.py).
PALETA_AVATAR = {
    "rojo": "#B91C1C", "naranja": "#C2410C", "mostaza": "#A16207", "verde": "#15803D",
    "turquesa": "#0F766E", "azul": "#1D4ED8", "violeta": "#6D28D9", "rosa": "#BE185D",
}
LETTERBOXD_URL = re.compile(r"(?:https?://)?(?:www\.)?letterboxd\.com/([^/?#]*)", re.IGNORECASE)
# Primeras partes de rutas de letterboxd.com que no son perfiles (un enlace a una película no da un usuario)
LETTERBOXD_NO_USUARIO = frozenset("film films list lists members search journal tag director actor settings activity".split())
ERROR_LETTERBOXD = "Escribe tu usuario de Letterboxd (de 2 a 20 letras, números o _) o pega el enlace a tu perfil"

PERFIL_INEXISTENTE =HTTPException(status_code=404, detail="Este perfil no existe o es privado")


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


def validar_letterboxd(texto: Optional[str]) -> tuple:
    """Usuario de Letterboxd, o la URL de su perfil -> (usuario tal cual o None si vacío, motivo del rechazo o None)."""
    valor = (texto or "").strip()
    if not valor:
        return None, None
    url = LETTERBOXD_URL.match(valor)
    valor = (url.group(1) if url else valor).removeprefix("@")
    if not re.fullmatch(r"[A-Za-z0-9_]{2,20}", valor) or valor.lower() in LETTERBOXD_NO_USUARIO:
        return None, ERROR_LETTERBOXD
    return valor, None


def color_avatar(perfil: Perfil) -> str:
    """El elegido o, si no hay, uno fijo sacado del nombre (siempre el mismo para el mismo usuario)."""
    if perfil.avatar_color in PALETA_AVATAR:
        return perfil.avatar_color
    return list(PALETA_AVATAR)[zlib.crc32(perfil.usuario.lower().encode()) % len(PALETA_AVATAR)]


class PerfilGuardar(SQLModel):
    usuario: str
    bio: Optional[str] = None
    visibilidad: Literal["privado", "publico"] = "privado"
    diario_publico: bool = False
    avatar_tipo: Literal["iniciales", "pelicula"] = "iniciales"
    avatar_color: Optional[str] = None  # None: el que sale del nombre
    avatar_pelicula_id: Optional[int] = None
    letterboxd_usuario: Optional[str] = None
    cines_publicos: bool = False


class Avatar(SQLModel):
    """Ya resuelto: tipo "pelicula" solo si la película sigue existiendo y tiene póster; si no, iniciales."""
    tipo: str
    color: str  # id de PALETA_AVATAR
    fondo: str  # su hex
    poster_url: Optional[str] = None


class PerfilSalida(SQLModel):
    usuario: Optional[str] = None  # None: aún no lo ha creado
    bio: Optional[str] = None
    visibilidad: str = "privado"
    diario_publico: bool = False
    avatar_tipo: str = "iniciales"
    avatar_color: Optional[str] = None
    avatar_pelicula_id: Optional[int] = None
    letterboxd_usuario: Optional[str] = None
    cines_publicos: bool = False
    avatar: Optional[Avatar] = None  # None: aún no hay usuario
    paleta_avatar: Dict[str, str] = PALETA_AVATAR
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


class Cifras(SQLModel):
    entradas: int
    este_anio: int  # año en curso en Madrid


class CinePublico(CineDiario):
    zona: Optional[str] = None


class PerfilPublico(SQLModel):
    usuario: str
    bio: Optional[str] = None
    avatar: Avatar
    letterboxd_usuario: Optional[str] = None
    diario_publico: bool = False
    cifras: Optional[Cifras] = None  # como el diario: solo si el perfil es público y diario_publico
    diario: Optional[DiarioPublico] = None  # solo si el perfil es público y diario_publico
    cines: Optional[List[CinePublico]] = None  # sus cines favoritos, solo si el perfil es público y cines_publicos


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


def _avatar(session: Session, perfil: Perfil) -> Avatar:
    color = color_avatar(perfil)
    pelicula = session.get(Pelicula, perfil.avatar_pelicula_id) if perfil.avatar_tipo == "pelicula" and perfil.avatar_pelicula_id else None
    if pelicula and pelicula.poster_url:
        return Avatar(tipo="pelicula", color=color, fondo=PALETA_AVATAR[color], poster_url=pelicula.poster_url)
    return Avatar(tipo="iniciales", color=color, fondo=PALETA_AVATAR[color])


def _salida(session: Session, perfil: Optional[Perfil]) -> PerfilSalida:
    if perfil is None:
        return PerfilSalida()
    return PerfilSalida.model_validate(perfil, update={"avatar": _avatar(session, perfil)})


@router.get("/me/perfil", response_model=PerfilSalida)
def leer_mi_perfil(usuario: Usuario = Depends(usuario_actual), session: Session = Depends(get_session)):
    return _salida(session, session.get(Perfil, _uid(usuario)))


@router.put("/me/perfil", response_model=PerfilSalida)
def guardar_mi_perfil(datos: PerfilGuardar, usuario: Usuario = Depends(usuario_actual),
                      session: Session = Depends(get_session)):
    nombre, motivo = validar_usuario(datos.usuario)
    if motivo:
        raise HTTPException(status_code=422, detail=motivo)
    bio = (datos.bio or "").strip() or None
    if bio and len(bio) > BIO_MAX:
        raise HTTPException(status_code=422, detail=f"La bio no puede pasar de {BIO_MAX} caracteres")
    letterboxd, motivo = validar_letterboxd(datos.letterboxd_usuario)
    if motivo:
        raise HTTPException(status_code=422, detail=motivo)
    if datos.avatar_color is not None and datos.avatar_color not in PALETA_AVATAR:
        raise HTTPException(status_code=422, detail="Ese color no está en la paleta")
    pelicula_id = None
    if datos.avatar_tipo == "pelicula":
        pelicula = session.get(Pelicula, datos.avatar_pelicula_id) if datos.avatar_pelicula_id else None
        if pelicula is None or not pelicula.poster_url:
            raise HTTPException(status_code=422, detail="Elige una película de nuestro catálogo que tenga póster")
        pelicula_id = pelicula.id
    valores = dict(usuario=nombre, bio=bio, visibilidad=datos.visibilidad, diario_publico=datos.diario_publico,
                   avatar_tipo=datos.avatar_tipo, avatar_color=datos.avatar_color, avatar_pelicula_id=pelicula_id,
                   letterboxd_usuario=letterboxd, cines_publicos=datos.cines_publicos)
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
    return _salida(session, session.get(Perfil, _uid(usuario)))


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
    salida = PerfilPublico(usuario=perfil.usuario, bio=perfil.bio, avatar=_avatar(session, perfil),
                           letterboxd_usuario=perfil.letterboxd_usuario, diario_publico=perfil.diario_publico)
    if perfil.cines_publicos:  # y es público, como el diario
        salida.cines = [CinePublico(slug=slug, nombre=nombre, zona=zona) for slug, nombre, zona in session.exec(
            select(Cine.slug, Cine.nombre, Cine.zona).join(CineFavorito, CineFavorito.cine_id == Cine.id)
            .where(CineFavorito.user_id == perfil.user_id).order_by(CineFavorito.creado_en, Cine.slug)
        ).all()]
    if perfil.diario_publico:  # y es público: un perfil privado nunca llega aquí
        suyas = DiarioEntrada.user_id == perfil.user_id
        total, este_anio = cifras(session, perfil.user_id)
        salida.cifras = Cifras(entradas=total, este_anio=este_anio)
        entradas = session.exec(
            select(DiarioEntrada).options(selectinload(DiarioEntrada.pelicula), selectinload(DiarioEntrada.cine))
            .where(suyas)
            .order_by(DiarioEntrada.fecha_vista.desc(), DiarioEntrada.creado_en.desc(), DiarioEntrada.id.desc())
            .offset((pagina - 1) * POR_PAGINA).limit(POR_PAGINA)
        ).all()
        salida.diario = DiarioPublico(total=total, pagina=pagina, por_pagina=POR_PAGINA,
                                      entradas=[EntradaPublica.model_validate(e) for e in entradas])
    return salida
