from functools import lru_cache
from pathlib import Path
from typing import Literal
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import Field, ValidationError, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
BACKEND_ENV_FILE = BACKEND_DIR / ".env"
REQUIRED_SETTINGS_ENV_NAMES = {
    "database_url": "SPLITMINT_DATABASE_URL",
    "jwt_secret_key": "SPLITMINT_JWT_SECRET_KEY",
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="SPLITMINT_",
        env_file=(str(BACKEND_ENV_FILE), ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "SplitMint API"
    environment: Literal["development", "test", "production"] = "development"
    debug: bool = False
    api_prefix: str = "/api/v1"

    database_url: str = Field(..., min_length=1)
    migration_database_url: str | None = Field(default=None, min_length=1)
    test_database_url: str | None = Field(default=None, min_length=1)
    allow_shared_test_database: bool = False
    db_disable_prepared_statements: bool | None = None
    frontend_origin: str = "http://127.0.0.1:5173"
    additional_cors_origins: list[str] = Field(default_factory=list)

    jwt_secret_key: str = Field(..., min_length=32)
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 30

    ai_enabled: bool = False
    openai_api_key: str | None = None
    openai_model: str = "gpt-5-mini"

    log_level: str = "INFO"

    @computed_field
    @property
    def effective_database_url(self) -> str:
        return self._normalize_postgres_url(self.database_url)

    @computed_field
    @property
    def effective_migration_database_url(self) -> str:
        return self._normalize_postgres_url(self.migration_database_url or self.database_url)

    @computed_field
    @property
    def disable_prepared_statements(self) -> bool:
        if self.db_disable_prepared_statements is not None:
            return self.db_disable_prepared_statements

        parsed = urlsplit(self.effective_database_url)
        host = (parsed.hostname or "").lower()
        is_supabase = host.endswith(".supabase.co") or host.endswith(".supabase.com")
        return parsed.scheme.startswith("postgres") and is_supabase and parsed.port == 6543

    @computed_field
    @property
    def cors_origins(self) -> list[str]:
        origins = [
            self.frontend_origin,
            "http://127.0.0.1:5173",
            "http://localhost:5173",
            "http://127.0.0.1:8080",
            "http://localhost:8080",
            *self.additional_cors_origins,
        ]
        expanded: list[str] = []
        for origin in origins:
            normalized = origin.rstrip("/")
            if not normalized:
                continue
            expanded.append(normalized)
            expanded.extend(self._loopback_variants(normalized))
        return list(dict.fromkeys(expanded))

    @staticmethod
    def _loopback_variants(origin: str) -> list[str]:
        parsed = urlsplit(origin)
        if parsed.hostname not in {"localhost", "127.0.0.1"}:
            return []
        port = f":{parsed.port}" if parsed.port else ""
        auth_prefix = ""
        if parsed.username:
            auth_prefix = parsed.username
            if parsed.password:
                auth_prefix = f"{auth_prefix}:{parsed.password}"
            auth_prefix = f"{auth_prefix}@"
        variants = []
        for host in ("localhost", "127.0.0.1"):
            netloc = f"{auth_prefix}{host}{port}"
            variant = urlunsplit((parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment))
            variants.append(variant.rstrip("/"))
        return variants

    @staticmethod
    def _normalize_postgres_url(url: str) -> str:
        parsed = urlsplit(url)
        if not parsed.scheme.startswith("postgres"):
            return url

        host = (parsed.hostname or "").lower()
        if not (host.endswith(".supabase.co") or host.endswith(".supabase.com")):
            return url

        query_pairs = parse_qsl(parsed.query, keep_blank_values=True)
        query = dict(query_pairs)
        if "sslmode" in query:
            return url

        query["sslmode"] = "require"
        return urlunsplit(
            (
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                urlencode(query, doseq=True),
                parsed.fragment,
            )
        )


@lru_cache
def get_settings() -> Settings:
    try:
        return Settings()
    except ValidationError as exc:
        missing_required = []
        invalid_settings = []
        for error in exc.errors():
            location = error.get("loc", ())
            field_name = location[0] if location else None
            error_type = error.get("type")
            if error_type == "missing" and field_name in REQUIRED_SETTINGS_ENV_NAMES:
                missing_required.append(REQUIRED_SETTINGS_ENV_NAMES[field_name])
                continue
            if field_name:
                invalid_settings.append(f"{field_name}: {error.get('msg', 'invalid value')}")
            else:
                invalid_settings.append(error.get("msg", "invalid value"))

        messages = []
        if missing_required:
            unique_missing = ", ".join(sorted(set(missing_required)))
            messages.append(f"Missing required settings: {unique_missing}.")
        if invalid_settings:
            messages.append(f"Invalid settings: {'; '.join(invalid_settings)}.")
        messages.append(
            f"Define these values in environment variables or `{BACKEND_ENV_FILE}` and restart."
        )
        raise RuntimeError(" ".join(messages)) from exc
