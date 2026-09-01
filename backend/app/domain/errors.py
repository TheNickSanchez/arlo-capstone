"""Domain error taxonomy → stable API error codes (SAD §4 error envelope).

`{ "error": { "code": "...", "message": "...", "arlo_id": "..." } }`

Raised from routers/services; translated to HTTP responses by the exception
handlers registered in `backend.app.main`. Keeping the taxonomy here (rather
than importing FastAPI in domain code) keeps `backend.app.domain` free of web
framework dependencies.
"""

from __future__ import annotations


class ArloError(Exception):
    """Base class for all domain errors carrying a stable error `code`."""

    code: str = "internal_error"
    status_code: int = 500

    def __init__(self, message: str, *, arlo_id: str | None = None) -> None:
        self.message = message
        self.arlo_id = arlo_id
        super().__init__(message)


class ValidationError(ArloError):
    code = "validation_error"
    status_code = 400


class ConflictError(ArloError):
    code = "conflict"
    status_code = 409


class NotFoundError(ArloError):
    code = "not_found"
    status_code = 404


class UnauthenticatedError(ArloError):
    code = "unauthenticated"
    status_code = 401


class PolicyDenyError(ArloError):
    code = "policy_deny"
    status_code = 403


class UpstreamUnavailableError(ArloError):
    code = "upstream_unavailable"
    status_code = 503
