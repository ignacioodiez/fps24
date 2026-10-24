import os
import re
import uvicorn
from fastapi import FastAPI, Depends, BackgroundTasks, HTTPException, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, SQLModel, or_, select
from typing import List, Optional
from datetime import date, datetime
from sqlalchemy import case, func, nulls_last
from sqlalchemy.orm import selectinload

from app.database.engine import get_session
from app.database.models import EstrenoProximo, Pase, Pelicula, PaseBase, PeliculaBase, PeliculaOculta
from app.run_scrapers import lanzar_todo 
from app.services.destacadas import SEMANAS_MAX, SEMANAS_MAX_ESTRENOS, leer_destacadas, leer_pagina, seleccionar_especiales
from app.services.cines import detalle_cine, listar_cines
from app.services.gestor_peliculas import EXCLUIDOS
from app.auth import Usuario, usuario_actual
from app.diario import router as diario_router
from app.perfil import router as perfil_router
from app.favoritos import router as favoritos_router
from app.admin import admin_actual, es_admin, router as admin_router
from app.newsletter.rutas import router as newsletter_router
from app.proximamente.estrenos import leer_estrenos as leer_estrenos_semana

app = FastAPI(title="fps24 API", version="1.0.0", lifespan=None) 

# El esquema lo gestiona Alembic (alembic upgrade head), no el arranque de la API.

# CORS
origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Diario del usuario (/diario...) y GET /pelicula/{id}/cines
app.include_router(diario_router)
# Perfil (/me/perfil, /usuarios/disponible) y perfil público (/u/{usuario})
app.include_router(perfil_router)
# Cines favoritos (/me/cines-favoritos)
app.include_router(favoritos_router)
# Panel de administración (/admin/...): 404 para quien no esté en ADMIN_EMAILS
app.include_router(admin_router)
# Newsletter semanal: /newsletter/suscribir, /newsletter/confirmar y /newsletter/baja
app.include_router(newsletter_router)

# --- ⚡ MODELOS DE RESPUESTA (AQUÍ ESTABA EL TAPÓN) ---

class PeliculaConId(PeliculaBase):
    id: int  
    fecha_estreno: Optional[date] = None  # estreno en cines en España; solo en la tabla, por eso se añade aquí

# "cine" ya no es columna: sale de cine.nombre (propiedad Pase.cine)
class PaseSalida(PaseBase):
    cine: str
    cine_slug: str  # para ordenar por los cines favoritos en el front (propiedad Pase.cine_slug)

class PaseConPelicula(PaseSalida):
    id: int
    pelicula: Optional[PeliculaConId] = None 

# 👇 AQUÍ ES DONDE AÑADIMOS LOS CAMPOS NUEVOS PARA QUE PASEN EL FILTRO
class PeliculaDetalle(PeliculaBase):
    id: int
    # Aseguramos que estos campos pasen al frontend:
    youtube_id: Optional[str] = None 
    imagenes_galeria: Optional[List[str]] = [] # <--- ¡ESTO FALTABA! 📸
    fecha_estreno: Optional[date] = None
    votos: Optional[int] = None  # para la vista rápida: nota apagada si hay pocos votos
    director: Optional[str] = None
    pases: List[PaseSalida] = []

class PaseConId(PaseSalida):
    id: int

class Semana(SQLModel):
    inicio: date
    fin: date

class Estreno(SQLModel):
    pelicula: PeliculaConId
    fecha_estreno: date
    votos: Optional[int] = None
    pases: int
    cines: int
    primera_sesion: PaseConId
    alternativas: List[PaseConId] = []  # ver EnLaSemana.alternativas
    sin_nota: bool  # relleno por nº de cines: no llega a la nota/votos mínimos

class Especial(SQLModel):
    pelicula: PeliculaConId
    pase: PaseConId
    alternativas: List[PaseConId] = []  # ver EnLaSemana.alternativas
    nota: float

class Destacadas(SQLModel):
    semana: Semana
    estrenos: List[Estreno]
    especiales: List[Especial]

# /estrenos y /especiales
class PeliculaSemana(PeliculaConId):
    id: Optional[int] = None  # None en los próximos estrenos sin sesiones (aún sin ficha): se identifican por tmdb_id
    votos: Optional[int] = None
    director: Optional[str] = None
    fecha_confirmada: Optional[bool] = None  # solo sin_sesiones: False = fecha prevista

class EnLaSemana(SQLModel):
    pelicula: PeliculaSemana
    sin_nota: bool  # estrenos: sin nota o con pocos votos (van al final)
    n_sesiones: int
    n_cines: int
    sesion: Optional[PaseConId] = None  # estrenos: la primera; especiales: la elegida como en /destacadas; None si sin_sesiones
    # El mismo día que `sesion`, la que se elegiría en cada uno de los otros cines (una por cine, por hora). El front
    # sugiere la de un cine favorito si la hay; si no, `sesion`.
    alternativas: List[PaseConId] = []
    # /estrenos: próximo estreno de TMDB (estreno_proximo) sin sesiones en nuestra BD. Van detrás, con 0 sesiones y cines
    sin_sesiones: bool = False

class PaginaSemana(SQLModel):
    semana: int
    desde: date
    hasta: date
    hay_anterior: bool
    hay_siguiente: bool
    peliculas: List[EnLaSemana]

class CineSalida(SQLModel):
    id: int
    slug: str
    nombre: str
    zona: Optional[str] = None
    tipo: Optional[str] = None
    direccion: Optional[str] = None
    web: Optional[str] = None
    telefono: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    # {"entrada", "entrada_laboral", "entrada_finde", "dia_espectador": {"dias", "precio"}, "notas"}: solo las que aplican
    tarifas: Optional[dict] = None
    sesiones_hoy: int  # pases activos de hoy (Madrid) desde ahora
    peliculas_hoy: int

# /cines/{slug}: la ficha de /cines más sus sesiones de los próximos 7 días
class SesionCine(SQLModel):
    id: int
    hora: str  # "HH:MM"
    fecha_hora: datetime
    link_compra: Optional[str] = None
    idioma: Optional[str] = None
    sala: Optional[str] = None
    precio: Optional[str] = None
    es_evento_especial: bool = False

class PeliculaCine(SQLModel):
    id: int
    titulo: str
    poster_url: Optional[str] = None
    nota_tmdb: Optional[float] = None
    votos: Optional[int] = None
    director: Optional[str] = None
    sesiones: List[SesionCine]

class DiaCine(SQLModel):
    fecha: date
    peliculas: List[PeliculaCine]

class CineDetalle(CineSalida):
    dias: List[DiaCine]
    solo_hoy: bool  # tiene sesiones hoy y ninguna desde mañana

# /peliculas/buscar
class PeliculaBuscada(SQLModel):
    id: int
    titulo: str
    titulo_original: Optional[str] = None  # solo si es distinto del título
    anio: Optional[int] = None
    director: Optional[str] = None
    poster_url: Optional[str] = None
    nota_tmdb: Optional[float] = None

class PeliculaBuscadaAdmin(PeliculaBuscada):
    id: Optional[int] = None  # None si sin_ficha
    tmdb_id: Optional[int] = None
    oculta: bool  # fuera de /destacadas, /estrenos y /especiales (pelicula_oculta; si sin_ficha, estreno_proximo.oculta)
    sin_ficha: bool = False  # próximo estreno de estreno_proximo que aún no está en pelicula: se oculta por tmdb_id

# --- SEGURIDAD ---

ACTUALIZAR_SECRET = os.getenv("ACTUALIZAR_SECRET")

def verificar_secreto(x_actualizar_secret: Optional[str] = Header(None)):
    if not ACTUALIZAR_SECRET or x_actualizar_secret != ACTUALIZAR_SECRET:
        raise HTTPException(status_code=401, detail="No autorizado")

# --- ENDPOINTS ---

@app.get("/pases", response_model=List[PaseConPelicula])
def leer_pases(session: Session = Depends(get_session)):
    pases = session.exec(
        select(Pase)
        .options(selectinload(Pase.pelicula), selectinload(Pase.cine_rel))
        .where(Pase.activo == True)
        .order_by(Pase.fecha_hora, Pase.id)
    ).all()
    return pases

# --- ENDPOINT DETALLE PELÍCULA 🎬 ---
@app.get("/pelicula/{pelicula_id}", response_model=PeliculaDetalle)
def leer_detalle_pelicula(pelicula_id: int, session: Session = Depends(get_session)):
    peli = session.get(Pelicula, pelicula_id)
    if not peli:
        raise HTTPException(status_code=404, detail="Película no encontrada")
    
    # Lista nueva: reasignar peli.pases desvincularía en BD los pases excluidos
    pases = sorted((p for p in peli.pases if p.activo), key=lambda p: (p.fecha_hora, p.id))
    return {**peli.model_dump(), "pases": pases}

# --- DESTACADAS DE LA SEMANA (estrenos y especiales) ---
@app.get("/destacadas", response_model=Destacadas)
def leer_destacadas_semana(session: Session = Depends(get_session)):
    return leer_destacadas(session)

# --- PÁGINAS DE ESTRENOS Y ESPECIALES, por semanas (0 = la actual, lunes-domingo en Madrid) ---
@app.get("/estrenos", response_model=PaginaSemana)
def leer_estrenos(semana: int = Query(0, ge=0, le=SEMANAS_MAX_ESTRENOS), session: Session = Depends(get_session)):
    return leer_estrenos_semana(session, semana)

@app.get("/especiales", response_model=PaginaSemana)
def leer_especiales(semana: int = Query(0, ge=0, le=SEMANAS_MAX), session: Session = Depends(get_session)):
    return leer_pagina(session, seleccionar_especiales, semana)

# ---------------------------------------------

# --- CINES: ficha, tarifas y lo que proyectan hoy (página "Salas y precios") ---
@app.get("/cines", response_model=List[CineSalida])
def leer_cines(session: Session = Depends(get_session)):
    return listar_cines(session)

@app.get("/cines/{slug}", response_model=CineDetalle)
def leer_cine(slug: str, session: Session = Depends(get_session)):
    cine = detalle_cine(session, slug)
    if cine is None:
        raise HTTPException(status_code=404, detail="Cine no encontrado")
    return cine

# --- BUSCAR PELÍCULAS (para apuntarlas en el diario): título u original, sin mayúsculas ni tildes ---
# Sin la extensión unaccent (no viene activada ni en local ni en Supabase): translate() con la misma tabla en SQL y en
# Python. Se traduce antes de lower() para no depender del locale de la BD.
CON_TILDE = "ÁÀÄÂÉÈËÊÍÌÏÎÓÒÖÔÚÙÜÛÑÇáàäâéèëêíìïîóòöôúùüûñç"
SIN_TILDE = "AAAAEEEEIIIIOOOOUUUUNCaaaaeeeeiiiioooouuuunc"
_SIN_TILDE = str.maketrans(CON_TILDE, SIN_TILDE)
_EXCLUIDA = re.compile("|".join(EXCLUIDOS), re.IGNORECASE)  # BONO, TARJETA REGALO…: limpiar_peliculas ya las borra

def _plano(columna):
    return func.lower(func.translate(columna, CON_TILDE, SIN_TILDE))

@app.get("/peliculas/buscar", response_model=List[PeliculaBuscada])
def buscar_peliculas(q: str = "", limite: int = Query(20, ge=1, le=30), session: Session = Depends(get_session)):
    consulta = " ".join(q.split()).translate(_SIN_TILDE).lower()
    if len(consulta) < 2:
        return []
    patron = re.sub(r"[!%_]", lambda m: "!" + m.group(), consulta)  # !, % y _ literales en LIKE
    titulo, original = _plano(Pelicula.titulo), _plano(func.coalesce(Pelicula.titulo_original, ""))
    empieza = or_(titulo.like(f"{patron}%", escape="!"), original.like(f"{patron}%", escape="!"))
    pelis = session.exec(
        select(Pelicula)
        .where(or_(titulo.like(f"%{patron}%", escape="!"), original.like(f"%{patron}%", escape="!")),
               select(Pase.id).where(Pase.pelicula_id == Pelicula.id).exists())  # ha pasado por la cartelera
        .order_by(case((empieza, 0), else_=1), nulls_last(Pelicula.votos.desc()),
                  nulls_last(Pelicula.fecha_estreno.desc()), Pelicula.id)
        .limit(limite + 10)  # margen por si alguna excluida sigue en la BD
    ).all()
    return [{**p.model_dump(), "titulo_original": p.titulo_original if p.titulo_original != p.titulo else None}
            for p in pelis if not _EXCLUIDA.search(p.titulo or "")][:limite]

# La misma búsqueda para el panel admin, con si cada una está oculta de las destacadas
@app.get("/admin/peliculas/buscar", response_model=List[PeliculaBuscadaAdmin])
def admin_buscar_peliculas(q: str = "", _: Usuario = Depends(admin_actual), session: Session = Depends(get_session)):
    pelis = buscar_peliculas(q, 30, session)
    ocultas = set(session.exec(select(PeliculaOculta.pelicula_id)
                               .where(PeliculaOculta.pelicula_id.in_([p["id"] for p in pelis]))).all())
    ya = {p["tmdb_id"] for p in pelis}
    titulo, original = _plano(EstrenoProximo.titulo), _plano(func.coalesce(EstrenoProximo.titulo_original, ""))
    patron = re.sub(r"[!%_]", lambda m: "!" + m.group(), " ".join(q.split()).translate(_SIN_TILDE).lower())
    proximos = session.exec(
        select(EstrenoProximo)
        .where(or_(titulo.like(f"%{patron}%", escape="!"), original.like(f"%{patron}%", escape="!")))
        .order_by(EstrenoProximo.fecha_es, EstrenoProximo.tmdb_id).limit(10)
    ).all() if len(patron) >= 2 else []  # como buscar_peliculas: al menos 2 letras
    return [{**p, "oculta": p["id"] in ocultas} for p in pelis] + [
        dict(tmdb_id=e.tmdb_id, titulo=e.titulo, anio=e.fecha_es.year, poster_url=f"https://image.tmdb.org/t/p/w342{e.poster_path}",
             titulo_original=e.titulo_original if e.titulo_original != e.titulo else None, oculta=e.oculta, sin_ficha=True)
        for e in proximos if e.tmdb_id not in ya]

# --- USUARIO: quién soy (JWT de Supabase Auth en Authorization: Bearer) ---
@app.get("/me")
def leer_me(usuario: Usuario = Depends(usuario_actual)):
    return {"id": usuario.id, "email": usuario.email, "es_admin": es_admin(usuario)}

@app.post("/actualizar")
def actualizar_todo(background_tasks: BackgroundTasks, _: None = Depends(verificar_secreto)):
    background_tasks.add_task(lanzar_todo)
    return {"mensaje": "🚀 Actualizando todo..."}

if __name__ == "__main__":
    # Ojo: aquí he puesto el nombre correcto del archivo si lo ejecutas directo
    # Si tu archivo se llama main.py, esto está bien:
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)