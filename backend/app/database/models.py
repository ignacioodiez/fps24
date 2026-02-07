from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime

# 1. ESQUELETO DE LA PELÍCULA
class PeliculaBase(SQLModel):
    titulo: str
    titulo_original: Optional[str] = None
    tmdb_id: Optional[int] = None
    poster_url: Optional[str] = None
    backdrop_url: Optional[str] = None # <--- NUEVO 🖼️
    sinopsis: Optional[str] = None
    nota_tmdb: Optional[float] = None
    anio: Optional[int] = None
    duracion: Optional[int] = None     # <--- NUEVO (minutos) ⏱️
    generos: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)

# 2. TABLA PELÍCULA
class Pelicula(PeliculaBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    pases: List["Pase"] = Relationship(back_populates="pelicula")

# 3. ESQUELETO DEL PASE
class PaseBase(SQLModel):
    cine: str
    sala: Optional[str] = None
    fecha_hora: datetime
    precio: Optional[str] = None
    link_compra: Optional[str] = None
    idioma: Optional[str] = "Español"
    es_evento_especial: bool = False
    pelicula_id: Optional[int] = Field(default=None, foreign_key="pelicula.id")

# 4. TABLA PASE
class Pase(PaseBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    pelicula: Optional[Pelicula] = Relationship(back_populates="pases")