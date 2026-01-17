from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel, Field

class Pase(SQLModel, table=True):
    # El identificador único de cada pase en nuestra base de datos
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Datos básicos
    cine: str  # Ej: "Cine Doré"
    pelicula: str  # Ej: "El Verdugo"
    
    # ¡IMPORTANTE! Esto no es texto, es un objeto de tiempo real.
    # Nos permitirá preguntar: "¿Qué echan el viernes a partir de las 20:00?"
    fecha_hora: datetime 
    
    # Datos útiles para el usuario
    sala: Optional[str] = None  # Ej: "Sala 1", "Sala Equis"
    precio: Optional[str] = None # Lo dejamos como texto por si es "3.50€" o "Gratis"
    idioma: Optional[str] = Field(default="VOSE")    
    # El botón de "Comprar"
    link_compra: str
    
    # Para ponerlo bonito luego (esto lo rellenaremos con otra API más adelante)
    poster_url: Optional[str] = None
    
    # Auditoría: Para saber cuándo scrapeamos esto
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Esto es un truco para evitar duplicados brutos:
    # Podríamos crear un ID único combinando cine + peli + hora, 
    # pero de momento lo dejamos simple.