from __future__ import annotations

from app.core.config import Settings

SECRET = "splitmint-tests-secret-key-with-at-least-32-bytes"


def test_supabase_runtime_url_adds_sslmode_when_missing() -> None:
    settings = Settings(
        database_url="postgresql+psycopg://postgres:secret@db.abcd1234.supabase.co:5432/postgres",
        db_disable_prepared_statements=None,
        jwt_secret_key=SECRET,
    )
    assert "sslmode=require" in settings.effective_database_url


def test_supabase_pooler_url_adds_sslmode_when_missing() -> None:
    settings = Settings(
        database_url=(
            "postgresql+psycopg://postgres.abcd1234:secret@aws-0-ap-south-1.pooler.supabase.com:"
            "6543/postgres"
        ),
        db_disable_prepared_statements=None,
        jwt_secret_key=SECRET,
    )
    assert "sslmode=require" in settings.effective_database_url


def test_transaction_pooler_defaults_to_disable_prepared_statements() -> None:
    settings = Settings(
        database_url=(
            "postgresql+psycopg://postgres.abcd1234:secret@aws-0-ap-south-1.pooler.supabase.com:"
            "6543/postgres"
        ),
        db_disable_prepared_statements=None,
        jwt_secret_key=SECRET,
    )
    assert settings.disable_prepared_statements is True


def test_direct_supabase_connection_keeps_prepared_statements_enabled() -> None:
    settings = Settings(
        database_url="postgresql+psycopg://postgres:secret@db.abcd1234.supabase.co:5432/postgres",
        db_disable_prepared_statements=None,
        jwt_secret_key=SECRET,
    )
    assert settings.disable_prepared_statements is False


def test_empty_db_disable_prepared_statements_falls_back_to_auto_detection() -> None:
    settings = Settings(
        database_url=(
            "postgresql+psycopg://postgres.abcd1234:secret@aws-0-ap-south-1.pooler.supabase.com:"
            "6543/postgres"
        ),
        db_disable_prepared_statements="",
        jwt_secret_key=SECRET,
    )
    assert settings.disable_prepared_statements is True


def test_supabase_url_preserves_existing_sslmode() -> None:
    settings = Settings(
        database_url=(
            "postgresql+psycopg://postgres:secret@db.abcd1234.supabase.co:5432/postgres?"
            "sslmode=verify-full"
        ),
        db_disable_prepared_statements=None,
        jwt_secret_key=SECRET,
    )
    assert "sslmode=verify-full" in settings.effective_database_url


def test_supabase_url_trims_sslmode_whitespace() -> None:
    settings = Settings(
        database_url=(
            "postgresql+psycopg://postgres.abcd1234:secret@aws-0-ap-south-1.pooler.supabase.com:"
            "5432/postgres?sslmode=require "
        ),
        db_disable_prepared_statements=None,
        jwt_secret_key=SECRET,
    )
    assert "sslmode=require" in settings.effective_database_url
    assert "sslmode=require+" not in settings.effective_database_url


def test_supabase_url_trims_outer_whitespace() -> None:
    settings = Settings(
        database_url=(
            "  postgresql+psycopg://postgres:secret@db.abcd1234.supabase.co:5432/postgres  "
        ),
        db_disable_prepared_statements=None,
        jwt_secret_key=SECRET,
    )
    assert settings.effective_database_url.startswith("postgresql+psycopg://postgres:secret@")


def test_migration_url_can_differ_from_runtime_url() -> None:
    settings = Settings(
        database_url=(
            "postgresql+psycopg://postgres.abcd1234:secret@aws-0-ap-south-1.pooler.supabase.com:"
            "6543/postgres"
        ),
        migration_database_url=(
            "postgresql+psycopg://postgres:secret@db.abcd1234.supabase.co:5432/postgres"
        ),
        db_disable_prepared_statements=None,
        jwt_secret_key=SECRET,
    )
    assert "pooler.supabase.com" in settings.effective_database_url
    assert "db.abcd1234.supabase.co" in settings.effective_migration_database_url
