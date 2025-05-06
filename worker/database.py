import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
import logging
from dotenv import load_dotenv
from typing import Iterator

# Load .env file from the project root if running locally/testing outside Docker
# In Docker, the env var should be set by docker-compose
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

log = logging.getLogger(__name__)

DATABASE_URL_SYNC = os.getenv("DATABASE_URL")

if not DATABASE_URL_SYNC:
    log.critical("Worker: DATABASE_URL environment variable not set.")
    raise EnvironmentError("DATABASE_URL environment variable not set for worker.")
else:
    # Ensure the URL uses the psycopg2 driver for synchronous worker access
    if "+asyncpg" in DATABASE_URL_SYNC:
        DATABASE_URL_SYNC = DATABASE_URL_SYNC.replace("+asyncpg", "+psycopg2")
        log.warning("Worker: Corrected DATABASE_URL to use psycopg2 driver.")
    elif not DATABASE_URL_SYNC.startswith("postgresql+psycopg2://") and DATABASE_URL_SYNC.startswith("postgresql://"):
         DATABASE_URL_SYNC = DATABASE_URL_SYNC.replace("postgresql://", "postgresql+psycopg2://", 1)
         log.warning("Worker: Assuming psycopg2 driver for DATABASE_URL.")
    elif not DATABASE_URL_SYNC.startswith("postgresql+psycopg2://"):
        log.error(f"Worker: Invalid DATABASE_URL scheme for synchronous operations: {DATABASE_URL_SYNC}")
        raise ValueError("Worker DATABASE_URL must use 'postgresql+psycopg2://' or 'postgresql://' driver scheme.")

    safe_db_url = DATABASE_URL_SYNC.split('@')[0] + '@...' if '@' in DATABASE_URL_SYNC else DATABASE_URL_SYNC
    log.info(f"Worker using Database URL: {safe_db_url}")


# Create synchronous engine for workers
sync_engine = create_engine(DATABASE_URL_SYNC, echo=False)

# Create session factory for synchronous sessions
SyncSessionFactory = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=sync_engine
)

# Context manager for yielding synchronous sessions
@contextmanager
def get_sync_session() -> Iterator[Session]: # <--- Corrected type hint
    """Provides a transactional scope around a series of operations."""
    session = SyncSessionFactory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        log.error("Worker DB session rolled back due to exception.", exc_info=True)
        raise
    finally:
        session.close()
