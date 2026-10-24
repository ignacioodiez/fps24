"""Panel de administración (/admin/...): solo para los correos de ADMIN_EMAILS. Para cualquier otro, con o sin sesión,
responde el mismo 404 que una ruta inexistente: no revela que el panel existe. Solo cifras agregadas, nombres de
usuario y recuentos: nunca contenido del diario, notas, comentarios, correos ni user_id."""
import logging
import os
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response
from sqlalchemy import func, text
from sqlalchemy.dialects.postgresql import insert
from sqlmodel import Field, Session, SQLModel, delete, select

from app.auth import Usuario, usuario_actual
from app.database.engine import get_session
from app.database.models import CineFavorito, DiarioEntrada, Pelicula, PeliculaOculta, Perfil

router = APIRouter(prefix="/admin")

# Hijo de uvicorn.error: hereda su handler y su nivel INFO (un logger propio sin configurar solo saca WARNING)
log = logging.getLogger("uvicorn.error").getChild("admin")

POR_PAGINA = 50
NO_ENCONTRADO = HTTPException(status_code=404, detail="Not Found")  # el mismo cuerpo que una ruta que no existe


def correos_admin() -> set:
    """ADMIN_EMAILS del entorno, separados por comas, en minúsculas. Se lee en cada llamada: sin reiniciar en tests."""
    return {c.strip().lower() for c in os.getenv("ADMIN_EMAILS", "").split(",") if c.strip()}


def es_admin(usuario: Usuario) -> bool:
    return bool(usuario.email) and usuario.email.strip().lower() in correos_admin()


def usuario_o_nada(authorization: Optional[str] = Header(None)) -> Optional[Usuario]:
    """usuario_actual sin su 401/503: aquí no tener sesión también es un 404."""
    try:
        return usuario_actual(authorization)
    except HTTPException:
        return None


def admin_actual(request: Request, usuario: Optional[Usuario] = Depends(usuario_o_nada)) -> Usuario:
    if usuario is None:
        raise NO_ENCONTRADO
    if not es_admin(usuario):
        log.warning("acceso admin denegado user_id=%s %s %s", usuario.id, request.method, request.url.path)
        raise NO_ENCONTRADO
    log.info("acceso admin user_id=%s %s %s", usuario.id, request.method, request.url.path)
    return usuario


# --- Resumen ---

class Resumen(SQLModel):
    usuarios_totales: int
    altas_7_dias: int
    altas_30_dias: int
    fuente_usuarios: str  # "auth.users" (cuentas de Supabase) o "perfil" (si el rol no puede leer el esquema auth)
    perfiles_con_usuario: int
    perfiles_publicos: int
    diarios_publicos: int  # perfil público con el diario visible: lo que de verdad se ve en /u/{usuario}
    entradas_diario: int
    favoritos: int
    peliculas_ocultas: int


def _puede_leer_auth(session: Session) -> bool:
    # CASE y no AND: has_table_privilege falla si la tabla no existe (Postgres local, sin esquema auth)
    return session.execute(text(
        "SELECT CASE WHEN to_regclass('auth.users') IS NULL THEN false "
        "ELSE has_schema_privilege('auth', 'USAGE') AND has_table_privilege('auth.users', 'SELECT') END"
    )).scalar()


def _contar(session: Session, consulta) -> int:
    return session.exec(consulta).one()


@router.get("/resumen", response_model=Resumen)
def resumen(_: Usuario = Depends(admin_actual), session: Session = Depends(get_session)):
    if _puede_leer_auth(session):
        fuente = "auth.users"
        totales, altas_7, altas_30 = session.execute(text(
            "SELECT count(*), count(*) FILTER (WHERE created_at >= now() - interval '7 days'), "
            "count(*) FILTER (WHERE created_at >= now() - interval '30 days') FROM auth.users"
        )).one()
    else:
        fuente = "perfil"
        totales, altas_7, altas_30 = session.execute(text(
            "SELECT count(*), count(*) FILTER (WHERE creado_en >= now() - interval '7 days'), "
            "count(*) FILTER (WHERE creado_en >= now() - interval '30 days') FROM perfil"
        )).one()
    publico = Perfil.visibilidad == "publico"
    return Resumen(
        usuarios_totales=totales, altas_7_dias=altas_7, altas_30_dias=altas_30, fuente_usuarios=fuente,
        perfiles_con_usuario=_contar(session, select(func.count()).select_from(Perfil)),
        perfiles_publicos=_contar(session, select(func.count()).where(publico)),
        diarios_publicos=_contar(session, select(func.count()).where(publico, Perfil.diario_publico)),
        entradas_diario=_contar(session, select(func.count()).select_from(DiarioEntrada)),
        favoritos=_contar(session, select(func.count()).select_from(CineFavorito)),
        peliculas_ocultas=_contar(session, select(func.count()).select_from(PeliculaOculta)),
    )


# --- Usuarios con perfil (solo recuentos) ---

class UsuarioAdmin(SQLModel):
    usuario: str
    visibilidad: str
    diario_publico: bool
    alta: datetime  # creación del perfil
    entradas: int
    favoritos: int


class PaginaUsuarios(SQLModel):
    pagina: int
    por_pagina: int
    total: int
    hay_siguiente: bool
    usuarios: List[UsuarioAdmin]


@router.get("/usuarios", response_model=PaginaUsuarios)
def usuarios(pagina: int = Query(1, ge=1), _: Usuario = Depends(admin_actual), session: Session = Depends(get_session)):
    entradas = (select(func.count()).where(DiarioEntrada.user_id == Perfil.user_id)
                .correlate(Perfil).scalar_subquery())
    favoritos = (select(func.count()).where(CineFavorito.user_id == Perfil.user_id)
                 .correlate(Perfil).scalar_subquery())
    filas = session.exec(
        select(Perfil.usuario, Perfil.visibilidad, Perfil.diario_publico, Perfil.creado_en, entradas, favoritos)
        .order_by(Perfil.creado_en.desc(), Perfil.usuario)
        .offset((pagina - 1) * POR_PAGINA).limit(POR_PAGINA)
    ).all()
    total = _contar(session, select(func.count()).select_from(Perfil))
    return PaginaUsuarios(
        pagina=pagina, por_pagina=POR_PAGINA, total=total, hay_siguiente=pagina * POR_PAGINA < total,
        usuarios=[UsuarioAdmin(usuario=u, visibilidad=v, diario_publico=d, alta=c, entradas=e, favoritos=f)
                  for u, v, d, c, e, f in filas],
    )


# --- Películas ocultas de /destacadas, /estrenos y /especiales (GET /admin/peliculas/buscar está en main.py) ---

class PeliculaOcultaSalida(SQLModel):
    id: int
    titulo: str
    anio: Optional[int] = None
    poster_url: Optional[str] = None
    motivo: Optional[str] = None
    creado_en: datetime


class Ocultar(SQLModel):
    motivo: Optional[str] = Field(default=None, max_length=500)


@router.get("/peliculas/ocultas", response_model=List[PeliculaOcultaSalida])
def ocultas(_: Usuario = Depends(admin_actual), session: Session = Depends(get_session)):
    filas = session.exec(
        select(Pelicula, PeliculaOculta).join(PeliculaOculta, PeliculaOculta.pelicula_id == Pelicula.id)
        .order_by(PeliculaOculta.creado_en.desc(), Pelicula.id)
    ).all()
    return [PeliculaOcultaSalida(id=p.id, titulo=p.titulo, anio=p.anio, poster_url=p.poster_url,
                                 motivo=o.motivo, creado_en=o.creado_en) for p, o in filas]


@router.post("/peliculas/{pelicula_id}/ocultar", status_code=204)
def ocultar(pelicula_id: int, cuerpo: Optional[Ocultar] = None, _: Usuario = Depends(admin_actual),
            session: Session = Depends(get_session)):
    if session.get(Pelicula, pelicula_id) is None:
        raise HTTPException(status_code=404, detail="Película no encontrada")
    motivo = ((cuerpo.motivo or "").strip() or None) if cuerpo else None
    # Idempotente: si ya estaba oculta, solo cambia el motivo
    session.exec(insert(PeliculaOculta).values(pelicula_id=pelicula_id, motivo=motivo)
                 .on_conflict_do_update(index_elements=["pelicula_id"], set_={"motivo": motivo}))
    session.commit()
    return Response(status_code=204)


@router.delete("/peliculas/{pelicula_id}/ocultar", status_code=204)
def mostrar(pelicula_id: int, _: Usuario = Depends(admin_actual), session: Session = Depends(get_session)):
    """Idempotente: si no estaba oculta, también 204."""
    session.exec(delete(PeliculaOculta).where(PeliculaOculta.pelicula_id == pelicula_id))
    session.commit()
    return Response(status_code=204)
