from __future__ import annotations

from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from sqlalchemy.exc import SQLAlchemyError

import app.db.models  # noqa: F401
from alembic import context
from app.core.config import get_settings
from app.core.startup import _format_database_target, _summarize_database_error
from app.db.base import Base

config = context.config
settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.effective_migration_database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=settings.effective_migration_database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    try:
        with connectable.connect() as connection:
            context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)

            with context.begin_transaction():
                context.run_migrations()
    except SQLAlchemyError as exc:
        target = _format_database_target(settings.effective_migration_database_url)
        detail = _summarize_database_error(exc, settings.effective_migration_database_url)
        raise RuntimeError(
            f"Migration database connectivity failed for {target}. {detail} "
            "Update SPLITMINT_MIGRATION_DATABASE_URL to a reachable PostgreSQL endpoint and retry."
        ) from exc


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
