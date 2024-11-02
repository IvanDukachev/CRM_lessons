from typing import AsyncGenerator

from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from config import DB_USER, DB_PASS, DB_HOST, DB_PORT, DB_NAME

DATABASE_URL = (
    f"postgresql+asyncpg://{DB_USER}:{DB_PASS}@"
    f"{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

metadata = MetaData()

engine = create_async_engine(DATABASE_URL, poolclass=NullPool)
async_session_maker = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Generate an asynchronous session for database operations.

    This function uses an asynchronous context manager to create
    and yield an `AsyncSession` instance. It ensures that the session
    is properly closed after usage, supporting asynchronous database
    operations with SQLAlchemy.

    Yields:
        An `AsyncSession` object configured for asynchronous database
        access.
    """
    async with async_session_maker() as session:
        yield session
