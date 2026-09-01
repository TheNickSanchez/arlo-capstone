"""Exception → JSON error envelope mapping (SAD §4).

`{ "error": { "code": "...", "message": "...", "arlo_id": "..." } }` with
stable codes: validation_error, conflict, not_found, unauthenticated,
policy_deny, upstream_unavailable.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from backend.app.domain.errors import ArloError

logger = logging.getLogger("arlo.api.errors")


def _envelope(code: str, message: str, arlo_id: str | None = None) -> dict:
    return {"error": {"code": code, "message": message, "arlo_id": arlo_id}}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ArloError)
    async def handle_arlo_error(_: Request, exc: ArloError) -> JSONResponse:
        if exc.status_code >= 500:
            logger.error("arlo_error code=%s message=%s", exc.code, exc.message)
        return JSONResponse(
            status_code=exc.status_code,
            content=_envelope(exc.code, exc.message, exc.arlo_id),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=_envelope("validation_error", str(exc.errors())),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled_exception")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_envelope("internal_error", "an unexpected error occurred"),
        )
