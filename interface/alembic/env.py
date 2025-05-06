# interface/alembic/env.py
import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool
from app.models import Base

from alembic import context

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Add project directory to sys.path for model imports
# Assumes env.py is in alembic/ directory, one level down from interface root
project_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_dir)


target_metadata = Base.metadata

# --- Get the ACTUAL database URL from the environment variable ---
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable not set.")

# --- Modify the URL to use the SYNCHRONOUS driver for Alembic ---
sync_db_url = DATABASE_URL
if "+asyncpg" in sync_db_url:
    sync_db_url = sync_db_url.replace("+asyncpg", "+psycopg2")
elif sync_db_url.startswith("postgresql://"):
    pass

# Ensure we have a valid synchronous URL prefix
if not sync_db_url.startswith(("postgresql+psycopg2://", "postgresql://")):
    raise ValueError(
        f"Could not derive a valid synchronous URL (psycopg2) "
        f"from DATABASE_URL='{DATABASE_URL}' for Alembic."
    )

# --- Update the config object with the SYNCHRONOUS URL ---
config.set_main_option('sqlalchemy.url', sync_db_url)
print(f"Alembic using synchronous URL: {sync_db_url.split('@')[0] + '@...'}") # Log safely


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
