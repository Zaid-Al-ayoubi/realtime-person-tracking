"""Shared FastAPI dependencies."""
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db

# Re-export so routers only import from here
__all__ = ["get_db"]
