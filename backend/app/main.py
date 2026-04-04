from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from time import perf_counter

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm.exc import StaleDataError

from app.api.router import api_router
from app.core.config import get_settings
from app.core.errors import AppError
from app.core.logging import configure_logging
from app.core.metrics import metrics_registry
from app.core.responses import error_response, success_response
from app.core.startup import validate_startup

settings = get_settings()
configure_logging(settings)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    validate_startup(settings)
    yield


app = FastAPI(title=settings.app_name, debug=settings.debug, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router, prefix=settings.api_prefix)


@app.get("/health")
def healthcheck() -> dict[str, object]:
    return success_response({"healthy": True, "environment": settings.environment})


@app.get("/metrics", response_class=PlainTextResponse)
def metrics() -> str:
    return metrics_registry.render_prometheus()


@app.middleware("http")
async def collect_http_metrics(request: Request, call_next):
    started_at = perf_counter()
    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    finally:
        route = request.scope.get("route")
        path = route.path if route and getattr(route, "path", None) else request.url.path
        metrics_registry.observe(
            method=request.method,
            path=path,
            status_code=status_code,
            duration_seconds=perf_counter() - started_at,
        )


@app.exception_handler(AppError)
async def handle_app_error(_: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response(code=exc.code, message=exc.message, details=exc.details),
    )


@app.exception_handler(RequestValidationError)
async def handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
    errors = [
        {
            "location": list(error["loc"]),
            "message": error["msg"],
            "type": error["type"],
        }
        for error in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content=error_response(
            code="validation_error",
            message="Request validation failed",
            details={"errors": errors},
        ),
    )


@app.exception_handler(StaleDataError)
async def handle_concurrency_error(_: Request, exc: StaleDataError) -> JSONResponse:
    logger.warning("Optimistic concurrency conflict: %s", exc)
    return JSONResponse(
        status_code=409,
        content=error_response(
            code="concurrency_conflict",
            message="The record was updated by another request. Please refresh and try again.",
        ),
    )


@app.exception_handler(IntegrityError)
async def handle_integrity_error(_: Request, exc: IntegrityError) -> JSONResponse:
    logger.warning("Integrity constraint error: %s", exc)
    return JSONResponse(
        status_code=409,
        content=error_response(
            code="integrity_conflict",
            message="Request conflicts with existing data constraints.",
        ),
    )


@app.exception_handler(OperationalError)
async def handle_operational_error(_: Request, exc: OperationalError) -> JSONResponse:
    logger.exception("Database operation failed: %s", exc)
    return JSONResponse(
        status_code=503,
        content=error_response(
            code="database_unavailable",
            message="Database operation failed. Please retry shortly.",
        ),
    )


@app.exception_handler(Exception)
async def handle_unexpected_error(_: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error")
    return JSONResponse(
        status_code=500,
        content=error_response(
            code="internal_server_error",
            message="An unexpected error occurred",
        ),
    )
