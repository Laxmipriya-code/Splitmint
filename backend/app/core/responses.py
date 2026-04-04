from __future__ import annotations

from typing import Any


def success_response(
    data: Any = None, *, message: str | None = None, meta: dict[str, Any] | None = None
) -> dict[str, Any]:
    payload: dict[str, Any] = {"status": "success", "data": data}
    if message:
        payload["message"] = message
    if meta:
        payload["meta"] = meta
    return payload


def error_response(
    *, code: str, message: str, details: dict[str, Any] | None = None
) -> dict[str, Any]:
    payload: dict[str, Any] = {"status": "error", "error": {"code": code, "message": message}}
    if details:
        payload["error"]["details"] = details
    return payload
