from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, Index, JSON, text, true  # <--- IMPORTANTE: Desde SQLAlchemy
from typing import Optional, List
from datetime import date, datetime, timezone


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
    youtube_id: Optional[str] = Field(default=None, description="ID del video de YouTube")
    created_at: datetime = Field(default_factory=datetime.now)

# 2. TABLA PELÍCULA
class Pelicula(PeliculaBase, table=True):
    __table_args__ = (Index("ix_pelicula_tmdb_id_unico", "tmdb_id", unique=True,
                            postgresql_where=text("tmdb_id IS NOT NULL")),)
    id: Optional[int] = Field(default=None, primary_key=True)
    imagenes_galeria: Optional[List[str]] = Field(default=None, sa_column=Column(JSON))
    # Solo en la tabla, no en PeliculaBase: la API no cambia. UTC; None: no se reintenta TMDB.
    tmdb_reintentar_en: Optional[datetime] = None
    # De TMDB (migración 0007), también solo en la tabla
    votos: Optional[int] = None
    fecha_estreno: Optional[date] = None  # estreno en cines en España (release_dates ES, tipo 2 o 3)
    idioma_original: Optional[str] = None
    director: Optional[str] = None
    imdb_id: Optional[str] = None
    tmdb_actualizado_en: Optional[datetime] = None  # UTC; último refresco desde TMDB
    pases: List["Pase"] = Relationship(back_populates="pelicula")

# 3. ESQUELETO DEL PASE
class PaseBase(SQLModel):
    sala: Optional[str] = None
    fecha_hora: datetime
    precio: Optional[str] = None
    link_compra: Optional[str] = None
    idioma: Optional[str] = "Español"
    es_evento_especial: bool = False
    pelicula_id: Optional[int] = Field(default=None, foreign_key="pelicula.id")

# 4. TABLA PASE
class Pase(PaseBase, table=True):
    # Identidad del pase (migración 0006); registrar_pase busca por ella.
    __table_args__ = (Index("ux_pase_identidad", "cine_id", "pelicula_id", "fecha_hora",
                            text("coalesce(idioma, '')"), text("coalesce(sala, '')"), unique=True),)
    id: Optional[int] = Field(default=None, primary_key=True)
    # Solo en la tabla, no en PaseBase: las respuestas de la API no cambian.
    cine_id: int = Field(foreign_key="cine.id", index=True)
    activo: bool = Field(default=True, sa_column_kwargs={"server_default": true()})
    visto_ultima_vez: Optional[datetime] = None  # UTC
    creado_en: Optional[datetime] = None  # UTC; NULL en los pases anteriores a la migración 0007
    pelicula: Optional[Pelicula] = Relationship(back_populates="pases")
    cine_rel: "Cine" = Relationship()

    @property
    def cine(self) -> str:
        """Nombre del cine, como el antiguo campo de texto: la API lo sigue devolviendo."""
        return self.cine_rel.nombre

# 5. TABLA CINE
class Cine(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    slug: str = Field(unique=True, index=True)
    nombre: str
    ultima_ejecucion_ok: Optional[datetime] = None
    # Ficha del cine (migración 0007)
    direccion: Optional[str] = None
    web: Optional[str] = None
    zona: Optional[str] = None
    tipo: Optional[str] = None
    telefono: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None


# 6. TABLA ALIAS: título de la web normalizado -> película (caché del emparejamiento).
# Las correcciones manuales no van aquí: están en app/services/correcciones_peliculas.py.
class PeliculaAlias(SQLModel, table=True):
    __tablename__ = "pelicula_alias"
    titulo_norm: str = Field(primary_key=True)
    pelicula_id: int = Field(foreign_key="pelicula.id", index=True, ondelete="CASCADE")
    creado_en: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))  # UTC
