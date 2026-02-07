# backend/crear_tablas.py
from sqlmodel import SQLModel
from app.database.engine import engine
# IMPORTANTE: Hay que importar los modelos para que SQLModel sepa que existen
from app.database.models import Pelicula, Pase 

def init_db():
    print("🔨 Construyendo la estructura de la base de datos...")
    SQLModel.metadata.create_all(engine)
    print("✅ ¡Tablas 'Pelicula' y 'Pase' creadas con éxito!")

if __name__ == "__main__":
    init_db()