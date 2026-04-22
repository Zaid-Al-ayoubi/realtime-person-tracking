"""
Celery application configuration.
Broker and result backend use Redis.
"""
from celery import Celery
from app.config import settings

celery_app = Celery(
    "store_analytics",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    worker_prefetch_multiplier=1,   # One task at a time — CV is CPU-heavy
    task_acks_late=True,
)
