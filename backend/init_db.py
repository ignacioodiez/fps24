from sqlmodel import SQLModel
from app.database.engine import engine
from app.database.models import Pase  # Importante importar el modelo para que SQLModel lo vea

def inicializar_db():
    print("🚀 Creando tablas en la base de datos nueva...")
    # Esto crea el archivo .db y las tablas si no existen
    SQLModel.metadata.create_all(engine)
    print("✅ ¡Tablas creadas! Ahora ya puedes lanzar los scrapers.")

if __name__ == "__main__":
    inicializar_db()