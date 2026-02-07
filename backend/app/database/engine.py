import os
from sqlmodel import SQLModel, create_engine, Session
from dotenv import load_dotenv

load_dotenv()

# 1. RECUPERAR URL
# Buscamos la variable DATABASE_URL. Si no existe, usamos SQLite local.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///database.db")

# 2. CORRECCIÓN AUTOMÁTICA DE URL (Vital para Render/Supabase)
# SQLAlchemy necesita que empiece por "postgresql://", pero a veces viene como "postgres://"
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# 3. ARGUMENTOS DE CONEXIÓN
connect_args = {}
# SQLite necesita esto para no quejarse de los hilos, Postgres NO lo necesita.
if "sqlite" in DATABASE_URL:
    connect_args = {"check_same_thread": False}

# 4. CREAR MOTOR
# pool_pre_ping=True ayuda a recuperar conexiones perdidas en la nube
engine = create_engine(
    DATABASE_URL, 
    echo=False, 
    connect_args=connect_args,
    pool_pre_ping=True 
)

def create_db_and_tables():
    """Crea las tablas automáticamente si no existen en la BD destino."""
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session