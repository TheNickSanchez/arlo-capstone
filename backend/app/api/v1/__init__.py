"""SAD §4 REST surface: `/api/v1`. Health/ready stay unversioned on the app."""

from fastapi import APIRouter

from . import auth, instances, webhooks

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(instances.router)
api_router.include_router(webhooks.router)

__all__ = ["api_router"]
