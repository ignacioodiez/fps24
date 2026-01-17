from sqlmodel import SQLModel, create_engine
import os

# Nombre del archivo de la base de datos
sqlite_file_name = "database.db"
# Ruta completa (para que no se pierda si ejecutas el script desde otro sitio)
base_dir = os.path.dirname(os.path.abspath(__file__))
database_path = os.path.join(base_dir, "..", "..", sqlite_file_name)
sqlite_url = f"sqlite:///{database_path}"

# Creamos el motor. 
# echo=True hará que veas en la terminal los comandos SQL (útil para depurar, luego lo quitamos)
engine = create_engine(sqlite_url, echo=True)

def create_db_and_tables():
    """Esta función mira tus modelos (models.py) y crea las tablas si no existen."""
    # Importante: Importar los modelos aquí para que SQLModel los reconozca antes de crear la tabla
    from app.database.models import Pase
    
    print("🏗️ Creando tablas en la base de datos...")
    SQLModel.metadata.create_all(engine)
    print("✅ Tablas listas.")

def get_session():
    """Esta función nos dará una 'sesión' para usar en los scrapers."""
    from sqlmodel import Session
    with Session(engine) as session:
        yield session