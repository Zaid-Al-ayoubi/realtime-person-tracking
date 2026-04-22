"""FastAPI entrypoint."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1.router import api_v1_router
from app.core.config import settings
from app.core.logging import configure_logging
from app.workers.scheduler import build_scheduler

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    logger.info("app.startup", extra={"env": settings.app_env})

    scheduler = build_scheduler()
    scheduler.start()
    app.state.scheduler = scheduler

    try:
        yield
    finally:
        scheduler.shutdown(wait=False)
        logger.info("app.shutdown")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Store Analytics API",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.include_router(api_v1_router)
    return app


app = create_app()
