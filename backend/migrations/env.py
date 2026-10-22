from logging.config import fileConfig

from alembic import context
from sqlmodel import SQLModel

# Misma URL y motor que la app (lee DATABASE_URL y corrige postgres:// -> postgresql://)
from app.database.engine import DATABASE_URL, engine
import app.database.models  # noqa: F401  registra Pelicula y Pase en SQLModel.metadata

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = SQLModel.metadata


def run_migrations_offline() -> None:
    """Genera el SQL sin conectar (alembic upgrade head --sql)."""
    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
