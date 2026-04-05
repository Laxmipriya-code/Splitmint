from __future__ import annotations

from sqlalchemy.exc import OperationalError

from app.core.startup import _format_database_target, _summarize_database_error


def _operational_error(message: str) -> OperationalError:
    return OperationalError("SELECT 1", {}, Exception(message))


def test_format_database_target_hides_credentials() -> None:
    target = _format_database_target(
        "postgresql+psycopg://splitmint:super-secret@127.0.0.1:55432/splitmint_test"
    )
    assert target == "127.0.0.1:55432/splitmint_test"
    assert "super-secret" not in target


def test_summarize_database_error_authentication_failure() -> None:
    error = _operational_error('FATAL: password authentication failed for user "splitmint"')
    assert (
        _summarize_database_error(error)
        == "Authentication failed for the configured database user."
    )


def test_summarize_database_error_connection_refused() -> None:
    error = _operational_error(
        'connection to server at "127.0.0.1", port 5432 failed: '
        "No connection could be made because the target machine actively refused it."
    )
    assert (
        _summarize_database_error(error)
        == "Connection was refused; check host, port, and server status."
    )


def test_summarize_database_error_ssl_required() -> None:
    error = _operational_error(
        'no pg_hba.conf entry for host "1.2.3.4", user "postgres", database "postgres", '
        "no encryption"
    )
    assert (
        _summarize_database_error(error)
        == "Server requires SSL. Add `?sslmode=require` to the PostgreSQL URL."
    )


def test_summarize_database_error_invalid_sslmode() -> None:
    error = _operational_error('connection is bad: invalid sslmode value: "require "')
    assert _summarize_database_error(error) == (
        "The PostgreSQL URL has an invalid `sslmode` value. Remove extra spaces and use "
        "`sslmode=require`."
    )


def test_summarize_database_error_prepared_statement_conflict() -> None:
    error = _operational_error('prepared statement "_pg3_0" does not exist')
    assert _summarize_database_error(error) == (
        "Prepared statements are incompatible with this pooler. Use a direct/session connection, "
        "or disable prepared statements for runtime connections."
    )


def test_summarize_database_error_supabase_direct_ipv6_unreachable() -> None:
    error = _operational_error(
        'connection to server at "2406:da12:b78:de13:254b:eae:5c3c:1f83", port 5432 failed: '
        "Network is unreachable"
    )
    assert _summarize_database_error(
        error,
        "postgresql+psycopg://postgres:secret@db.abcd1234.supabase.co:5432/postgres",
    ) == (
        "This Supabase direct connection uses IPv6 by default, but the current runtime "
        "cannot reach IPv6. On Render, switch to the Supavisor session pooler URL "
        "(port 5432), or enable Supabase's IPv4 add-on."
    )
