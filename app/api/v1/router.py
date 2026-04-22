from fastapi import APIRouter

from app.api.v1 import employees, customers, cameras, visits, incidents, analytics

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(employees.router, prefix="/employees", tags=["Employees"])
api_router.include_router(customers.router, prefix="/customers", tags=["Customers"])
api_router.include_router(cameras.router, prefix="/cameras", tags=["Cameras"])
api_router.include_router(visits.router, prefix="/visits", tags=["Visits"])
api_router.include_router(incidents.router, prefix="/incidents", tags=["Incidents"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])
