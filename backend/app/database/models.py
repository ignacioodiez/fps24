from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import Optional

class Pase(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    cine: str
    pelicula: str
    fecha_hora: datetime
    sala: Optional[str] = None
    precio: Optional[str] = None
    link_compra: Optional[str] = None
    poster_url: Optional[str] = None
    idioma: Optional[str] = "Español"
    
   # --- NUEVAS COLUMNAS ---
    es_evento_especial: bool = Field(default=False)
    nota_tmdb: Optional[float] = Field(default=None) # Ej: 7.8
    anio: Optional[int] = Field(default=None)        # Ej: 1994