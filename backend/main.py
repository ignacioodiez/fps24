from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware  # <--- IMPORTANTE
from sqlmodel import Session, select
from app.database.engine import get_session
from app.database.models import Pase

app = FastAPI(title="fps24 API")

# --- CONFIGURACIÓN CORS (El permiso para que el frontend hable con el backend) ---
origins = [
    "http://localhost:3000",    # React / Next.js
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,      # Qué webs pueden pedir datos
    allow_credentials=True,
    allow_methods=["*"],        # Permitir todos los métodos (GET, POST...)
    allow_headers=["*"],
)
# ---------------------------------------------------------------------------------

@app.get("/")
def read_root():
    return {"mensaje": "¡Bienvenido a la API de fps24! 🎬"}

@app.get("/pases")
def leer_pases(session: Session = Depends(get_session)):
    """Devuelve todas las películas guardadas en la base de datos"""
    pases = session.exec(select(Pase)).all()
    return pases