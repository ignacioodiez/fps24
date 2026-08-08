import os
import uvicorn
from fastapi import FastAPI, Depends, BackgroundTasks, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, select
from typing import List, Optional
from sqlalchemy.orm import selectinload

from app.database.engine import get_session, create_db_and_tables
from app.database.models import Pase, Pelicula, PaseBase, PeliculaBase
from app.run_scrapers import lanzar_todo 
from app.scrapers.cines.cine_paz import scrapear_cine_paz
from app.scrapers.cines.verdi import scrapear_verdi

app = FastAPI(title="fps24 API", version="1.0.0", lifespan=None) 

@app.on_event("startup")
def on_startup():
    create_db_and_tables()

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

class PaseConPelicula(PaseBase):
    id: int
    pelicula: Optional[PeliculaConId] = None 

# 👇 AQUÍ ES DONDE AÑADIMOS LOS CAMPOS NUEVOS PARA QUE PASEN EL FILTRO
class PeliculaDetalle(PeliculaBase):
    id: int
    # Aseguramos que estos campos pasen al frontend:
    youtube_id: Optional[str] = None 
    imagenes_galeria: Optional[List[str]] = [] # <--- ¡ESTO FALTABA! 📸
    pases: List[PaseBase] = []

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
        .options(selectinload(Pase.pelicula)) 
        .order_by(Pase.fecha_hora)
    ).all()
    return pases

# --- ENDPOINT DETALLE PELÍCULA 🎬 ---
@app.get("/pelicula/{pelicula_id}", response_model=PeliculaDetalle)
def leer_detalle_pelicula(pelicula_id: int, session: Session = Depends(get_session)):
    peli = session.get(Pelicula, pelicula_id)
    if not peli:
        raise HTTPException(status_code=404, detail="Película no encontrada")
    
    # Ordenamos pases
    peli.pases.sort(key=lambda x: x.fecha_hora)
    
    # FastAPI ahora verá que 'imagenes_galeria' está en PeliculaDetalle
    # y dejará pasar los datos que vienen de la BD.
    return peli

# ---------------------------------------------

@app.post("/actualizar")
def actualizar_todo(background_tasks: BackgroundTasks, _: None = Depends(verificar_secreto)):
    background_tasks.add_task(lanzar_todo)
    return {"mensaje": "🚀 Actualizando todo..."}

@app.post("/test/paz")
def test_cine_paz(background_tasks: BackgroundTasks):
    background_tasks.add_task(scrapear_cine_paz)
    return {"mensaje": "🎹 Test Cine Paz lanzado."}

@app.post("/test/verdi")
def test_cine_verdi(background_tasks: BackgroundTasks):
    background_tasks.add_task(scrapear_verdi)
    return {"mensaje": "🎹 Test Cine Verdi lanzado."}

if __name__ == "__main__":
    # Ojo: aquí he puesto el nombre correcto del archivo si lo ejecutas directo
    # Si tu archivo se llama main.py, esto está bien:
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)