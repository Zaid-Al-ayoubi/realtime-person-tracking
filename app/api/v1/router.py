"""Aggregated v1 router."""
from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import analytics, cameras, customers, employees, health, incidents, visits

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(health.router)
api_v1_router.include_router(cameras.router)
api_v1_router.include_router(employees.router)
api_v1_router.include_router(customers.router)
api_v1_router.include_router(visits.router)
api_v1_router.include_router(incidents.router)
api_v1_router.include_router(analytics.router)
