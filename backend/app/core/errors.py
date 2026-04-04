from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class AppError(Exception):
    message: str
    status_code: int
    code: str
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = {"code": self.code, "message": self.message}
        if self.details:
            payload["details"] = self.details
        return payload


class BadRequestError(AppError):
    def __init__(
        self, message: str, *, code: str = "bad_request", details: dict[str, Any] | None = None
    ):
        super().__init__(message=message, status_code=400, code=code, details=details or {})


class UnauthorizedError(AppError):
    def __init__(self, message: str = "Authentication required"):
        super().__init__(message=message, status_code=401, code="unauthorized", details={})


class ForbiddenError(AppError):
    def __init__(self, message: str = "Access denied"):
        super().__init__(message=message, status_code=403, code="forbidden", details={})


class NotFoundError(AppError):
    def __init__(self, message: str = "Resource not found", *, code: str = "not_found"):
        super().__init__(message=message, status_code=404, code=code, details={})


class ConflictError(AppError):
    def __init__(self, message: str, *, details: dict[str, Any] | None = None):
        super().__init__(message=message, status_code=409, code="conflict", details=details or {})
