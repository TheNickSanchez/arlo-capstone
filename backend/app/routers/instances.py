"""Instances API (SAD §4). Implement in @backend.eng (*develop-be).

POST   /api/v1/instances
GET    /api/v1/instances
GET    /api/v1/instances/{arlo_id}
GET    /api/v1/instances/{arlo_id}/audit
POST   /api/v1/instances/{arlo_id}/approve
POST   /api/v1/instances/{arlo_id}/reject
POST   /api/v1/instances/{arlo_id}/cancel
"""

from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/instances", tags=["instances"])
