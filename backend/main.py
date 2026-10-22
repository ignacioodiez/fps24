import os
import uvicorn
from fastapi import FastAPI, Depends, BackgroundTasks, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, SQLModel, select
from typing import List, Optional
from datetime import date
from sqlalchemy.orm import selectinload

from app.database.engine import get_session
from app.database.models import Pase, Pelicula, PaseBase, PeliculaBase
from app.run_scrapers import lanzar_todo 
from app.services.destacadas import leer_destacadas
from app.services.cines import listar_cines

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

# --- ⚡ MODELOS DE RESPUESTA (AQUÍ ESTABA EL TAPÓN) ---

class PeliculaConId(PeliculaBase):
    id: int  
    fecha_estreno: Optional[date] = None  # estreno en cines en España; solo en la tabla, por eso se añade aquí

# "cine" ya no es columna: sale de cine.nombre (propiedad Pase.cine)
class PaseSalida(PaseBase):
    cine: str

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
    sin_nota: bool  # relleno por nº de cines: no llega a la nota/votos mínimos

class Especial(SQLModel):
    pelicula: PeliculaConId
    pase: PaseConId
    nota: float

class Destacadas(SQLModel):
    semana: Semana
    estrenos: List[Estreno]
    especiales: List[Especial]

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

# ---------------------------------------------

# --- CINES: ficha, tarifas y lo que proyectan hoy (página "Salas y precios") ---
@app.get("/cines", response_model=List[CineSalida])
def leer_cines(session: Session = Depends(get_session)):
    return listar_cines(session)

@app.post("/actualizar")
def actualizar_todo(background_tasks: BackgroundTasks, _: None = Depends(verificar_secreto)):
    background_tasks.add_task(lanzar_todo)
    return {"mensaje": "🚀 Actualizando todo..."}

if __name__ == "__main__":
    # Ojo: aquí he puesto el nombre correcto del archivo si lo ejecutas directo
    # Si tu archivo se llama main.py, esto está bien:
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)