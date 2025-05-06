import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from dotenv import load_dotenv
import logging
from typing import AsyncGenerator

log = logging.getLogger(__name__)

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    log.critical("DATABASE_URL environment variable not set. Cannot connect to database.")
    raise EnvironmentError("DATABASE_URL environment variable not set.")
else:
    safe_db_url = DATABASE_URL.split('@')[0] + '@...' if '@' in DATABASE_URL else DATABASE_URL
    log.info(f"Database URL loaded: {safe_db_url}")


# Ensure the URL uses the asyncpg driver for FastAPI
if not DATABASE_URL.startswith("postgresql+asyncpg://"):
    if DATABASE_URL.startswith("postgresql+psycopg2://"):
        DATABASE_URL = DATABASE_URL.replace("postgresql+psycopg2://", "postgresql+asyncpg://", 1)
        log.warning("Corrected DATABASE_URL to use asyncpg driver.")
    elif DATABASE_URL.startswith("postgresql://"):
        DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
        log.warning("Assuming asyncpg driver for DATABASE_URL.")
    else:
        log.error(f"Invalid DATABASE_URL scheme for async operations: {DATABASE_URL}")
        raise ValueError("DATABASE_URL must use the 'postgresql+asyncpg://' driver scheme for asynchronous operations.")


# Create the async engine
# echo=True is good for dev, logs SQL statements
engine = create_async_engine(DATABASE_URL, echo=True)


AsyncSessionFactory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Dependency to get an async session for FastAPI endpoints
async def get_async_session() -> AsyncGenerator[AsyncSession, None]: # <--- Corrected type hint
    async with AsyncSessionFactory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        # finally:
            # The 'async with AsyncSessionFactory() as session:' context manager
            # handles closing the session automatically.
            # await session.close() # Not strictly needed here

# Base class for models (can be imported from models.py)
# from .models import Base

# Alembic handles DB initialization/migration