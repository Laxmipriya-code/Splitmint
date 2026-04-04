from __future__ import annotations

import os
from pathlib import Path

import pytest
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from alembic import command

TEST_JWT_SECRET = "splitmint-tests-secret-key-with-at-least-32-bytes"

os.environ.setdefault("SPLITMINT_ENVIRONMENT", "test")
os.environ.setdefault("SPLITMINT_FRONTEND_ORIGIN", "http://127.0.0.1:5173")
os.environ.setdefault("SPLITMINT_JWT_SECRET_KEY", TEST_JWT_SECRET)
os.environ.setdefault("SPLITMINT_AI_ENABLED", "false")


def _run_migrations(database_url: str) -> None:
    alembic_ini = Path(__file__).resolve().parents[1] / "alembic.ini"
    config = Config(str(alembic_ini))
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, "head")


@pytest.fixture(scope="session")
def postgres_test_db() -> str:
    test_database_url = os.getenv("SPLITMINT_TEST_DATABASE_URL")
    from app.core.config import get_settings

    settings = get_settings()
    if not test_database_url:
        test_database_url = settings.test_database_url

    if not test_database_url:
        raise RuntimeError(
            "SPLITMINT_TEST_DATABASE_URL is required for PostgreSQL-backed tests. "
            "Set it as an environment variable or in backend/.env, and point it to a dedicated "
            "test database."
        )

    if (
        test_database_url == settings.database_url
        and not settings.allow_shared_test_database
    ):
        raise RuntimeError(
            "SPLITMINT_TEST_DATABASE_URL must target a dedicated test database and cannot match "
            "SPLITMINT_DATABASE_URL. Set SPLITMINT_ALLOW_SHARED_TEST_DATABASE=true only if you "
            "explicitly want tests to truncate your runtime database."
        )

    os.environ["SPLITMINT_DATABASE_URL"] = test_database_url
    os.environ["SPLITMINT_MIGRATION_DATABASE_URL"] = test_database_url

    from app.db.session import reset_session_state

    get_settings.cache_clear()
    reset_session_state()
    _run_migrations(test_database_url)
    yield test_database_url
    get_settings.cache_clear()
    reset_session_state()


@pytest.fixture(autouse=True)
def _truncate_all_tables(postgres_test_db: str) -> None:
    from app.db.session import get_engine

    with get_engine().begin() as connection:
        connection.execute(
            text(
                "TRUNCATE TABLE product_events, expense_splits, expenses, participants, "
                "refresh_tokens, groups, users RESTART IDENTITY CASCADE"
            )
        )


@pytest.fixture()
def client(postgres_test_db: str) -> TestClient:
    from app.main import app

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def db_session(postgres_test_db: str) -> Session:
    from app.db.session import get_session_factory

    db = get_session_factory()()
    try:
        yield db
    finally:
        db.close()


def register_and_login(
    client: TestClient, *, email: str = "owner@example.com", password: str = "Password123!"
) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "display_name": "Owner"},
    )
    assert response.status_code == 201, response.text
    payload = response.json()["data"]
    return {
        "access_token": payload["tokens"]["access_token"],
        "refresh_token": payload["tokens"]["refresh_token"],
    }


def auth_headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}
