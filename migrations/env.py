"""Alembic environment (async). The database URL comes from `sqlalchemy.url` when a
caller sets it (tests), otherwise from DATABASE_URL / .env."""
import asyncio
from logging.config import fileConfig

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from knowledge_transfer.db import (
    models,  # noqa: F401  registers tables on Base.metadata
)
from knowledge_transfer.db.base import Base
from knowledge_transfer.db.session import database_url

config = context.config
if config.config_file_name is not None and config.attributes.get("configure_logger", True):
    fileConfig(config.config_file_name, disable_existing_loggers=False)

if not config.get_main_option("sqlalchemy.url"):
    load_dotenv()
    config.set_main_option("sqlalchemy.url", database_url())

target_metadata = Base.metadata


def _configure(**kwargs) -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        target_metadata=target_metadata,
        compare_type=True,
        render_as_batch=url.startswith("sqlite"),  # SQLite needs batch mode for ALTER
        **kwargs,
    )


def run_migrations_offline() -> None:
    """Emit SQL to stdout instead of running it (`alembic upgrade head --sql`)."""
    _configure(url=config.get_main_option("sqlalchemy.url"), literal_binds=True,
               dialect_opts={"paramstyle": "named"})
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    _configure(connection=connection)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    engine = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with engine.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_async_migrations())
