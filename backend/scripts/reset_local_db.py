from __future__ import annotations

import argparse
from pathlib import Path

from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy.engine.url import make_url

from alembic import command
from app.core.config import get_settings


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Reset local PostgreSQL schema and migrate to head."
    )
    parser.add_argument(
        "--force-nonlocal",
        action="store_true",
        help="Allow reset even when database host is not localhost/127.0.0.1.",
    )
    parser.add_argument(
        "--seed",
        action="store_true",
        help="Seed deterministic demo data after migration.",
    )
    return parser.parse_args()


def assert_safe_target(database_url: str, *, force_nonlocal: bool) -> None:
    parsed = make_url(database_url)
    host = parsed.host or ""
    if host not in {"localhost", "127.0.0.1"} and not force_nonlocal:
        raise RuntimeError(
            "Refusing to reset non-local database target. Use --force-nonlocal if intentional."
        )


def reset_schema(database_url: str) -> None:
    engine = create_engine(database_url, isolation_level="AUTOCOMMIT", future=True)
    try:
        with engine.connect() as connection:
            connection.exec_driver_sql("DROP SCHEMA IF EXISTS public CASCADE")
            connection.exec_driver_sql("CREATE SCHEMA public")
    finally:
        engine.dispose()


def run_migrations(database_url: str) -> None:
    alembic_ini = Path(__file__).resolve().parents[1] / "alembic.ini"
    config = Config(str(alembic_ini))
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, "head")


def main() -> None:
    args = parse_args()
    settings = get_settings()
    target_database_url = settings.effective_migration_database_url

    if settings.environment == "production":
        raise RuntimeError("Refusing to reset database while SPLITMINT_ENVIRONMENT=production.")

    assert_safe_target(target_database_url, force_nonlocal=args.force_nonlocal)
    reset_schema(target_database_url)
    run_migrations(target_database_url)

    if args.seed:
        from scripts.seed_sample_data import main as seed_main

        seed_main()

    print("Database reset complete.")


if __name__ == "__main__":
    main()
