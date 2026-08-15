import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base

# PostgreSQL connection string
# In production, this should come from the environment.
DATABASE_URL = os.getenv(
    "KOKKOPI_DATABASE_URL", 
    "postgresql+asyncpg://postgres:postgres@localhost:5432/kokkopi"
)

# Global engine and session factory
engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

Base = declarative_base()

async def get_db():
    """Dependency for getting async DB sessions in FastAPI routes."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
