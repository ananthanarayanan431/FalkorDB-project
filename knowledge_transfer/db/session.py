"""Async engine and session factory. Configure with DATABASE_URL."""
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from knowledge_transfer.core.config import get_settings


def database_url() -> str:
    return get_settings().database_url


def make_engine(url: str | None = None, **kwargs) -> AsyncEngine:
    return create_async_engine(url or database_url(), pool_pre_ping=True, **kwargs)


def make_sessionmaker(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


async def ping(sessions: async_sessionmaker[AsyncSession]) -> bool:
    try:
        async with sessions() as db:
            await db.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
