from __future__ import annotations

from pathlib import Path

from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, text
from sqlalchemy.engine.url import make_url
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import Settings
from app.db.session import get_engine

WEAK_JWT_SECRETS = {
    "change-me-access-secret-with-at-least-32-bytes",
    "replace-with-a-long-random-secret-at-least-32-bytes",
}


def validate_startup(settings: Settings) -> None:
    failures: list[str] = []
    db_connected = True

    if settings.jwt_secret_key in WEAK_JWT_SECRETS or len(settings.jwt_secret_key) < 32:
        failures.append(
            "SPLITMINT_JWT_SECRET_KEY must be a strong random value with at least 32 characters."
        )

    if settings.ai_enabled and not settings.openai_api_key:
        failures.append("SPLITMINT_OPENAI_API_KEY is required when SPLITMINT_AI_ENABLED=true.")

    try:
        _validate_database_connectivity(settings.effective_database_url)
    except RuntimeError as exc:
        db_connected = False
        failures.append(str(exc))

    if db_connected:
        try:
            _validate_migration_head(settings.effective_migration_database_url)
        except RuntimeError as exc:
            failures.append(str(exc))

    if failures:
        joined = "\n- ".join(failures)
        raise RuntimeError(f"Startup validation failed:\n- {joined}")


def _validate_database_connectivity(database_url: str) -> None:
    try:
        with get_engine().connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        target = _format_database_target(database_url)
        detail = _summarize_database_error(exc, database_url)
        raise RuntimeError(
            f"Database connectivity failed for {target}. {detail} Verify SPLITMINT_DATABASE_URL "
            "points to your running PostgreSQL instance."
        ) from exc


def _validate_migration_head(migration_database_url: str) -> None:
    alembic_ini = Path(__file__).resolve().parents[2] / "alembic.ini"
    config = Config(str(alembic_ini))
    config.set_main_option("sqlalchemy.url", migration_database_url)
    script = ScriptDirectory.from_config(config)
    expected_head = script.get_current_head()

    engine = None
    try:
        engine = create_engine(migration_database_url, future=True, pool_pre_ping=True)
        with engine.connect() as connection:
            context = MigrationContext.configure(connection)
            current_revision = context.get_current_revision()
    except SQLAlchemyError as exc:
        raise RuntimeError(
            "Unable to verify migration head because database connection failed. "
            "Confirm the credentials in SPLITMINT_DATABASE_URL (and optionally "
            "SPLITMINT_MIGRATION_DATABASE_URL) match your PostgreSQL instance."
        ) from exc
    finally:
        if engine is not None:
            engine.dispose()

    if current_revision != expected_head:
        raise RuntimeError(
            "Database schema is out of date. Run `python -m alembic upgrade head` "
            f"(current={current_revision}, expected={expected_head})."
        )


def _format_database_target(database_url: str) -> str:
    parsed = make_url(database_url)
    host = parsed.host or "localhost"
    port = parsed.port or 5432
    database = parsed.database or "<unknown>"
    return f"{host}:{port}/{database}"


def _summarize_database_error(exc: SQLAlchemyError, database_url: str | None = None) -> str:
    raw = str(getattr(exc, "orig", exc)).replace("\n", " ").strip()
    lowered = raw.lower()
    if "password authentication failed" in lowered:
        return "Authentication failed for the configured database user."
    if "no pg_hba.conf entry" in lowered and "no encryption" in lowered:
        return "Server requires SSL. Add `?sslmode=require` to the PostgreSQL URL."
    if "prepared statement" in lowered and "does not exist" in lowered:
        return (
            "Prepared statements are incompatible with this pooler. Use a direct/session connection, "
            "or disable prepared statements for runtime connections."
        )
    if "network is unreachable" in lowered:
        if database_url and _is_supabase_direct_connection(database_url):
            return (
                "This Supabase direct connection uses IPv6 by default, but the current runtime "
                "cannot reach IPv6. On Render, switch to the Supavisor session pooler URL "
                "(port 5432), or enable Supabase's IPv4 add-on."
            )
        return "Network was unreachable; check outbound network support, DNS, and routing."
    if "connection refused" in lowered or "actively refused" in lowered:
        return "Connection was refused; check host, port, and server status."
    if "could not translate host name" in lowered or "name or service not known" in lowered:
        return "Host could not be resolved."
    if raw:
        return f"Driver detail: {raw}"
    return "No additional driver detail was provided."


def _is_supabase_direct_connection(database_url: str) -> bool:
    parsed = make_url(database_url)
    host = (parsed.host or "").lower()
    return host.endswith(".supabase.co") and (parsed.port or 5432) == 5432
