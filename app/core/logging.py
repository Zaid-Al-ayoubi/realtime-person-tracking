"""
Centralized logging configuration.

Call `configure_logging()` once at app startup. All modules then just do:
    import logging
    logger = logging.getLogger(__name__)
"""
from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone

from app.core.config import settings


class JsonFormatter(logging.Formatter):
    """Minimal JSON formatter for structured logs in production."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        # Include any extras attached via logger.info("...", extra={"key": val})
        for key, value in record.__dict__.items():
            if key in _STANDARD_LOGRECORD_FIELDS:
                continue
            payload[key] = value
        return json.dumps(payload, default=str)


_STANDARD_LOGRECORD_FIELDS = {
    "args", "asctime", "created", "exc_info", "exc_text", "filename",
    "funcName", "levelname", "levelno", "lineno", "message", "module",
    "msecs", "msg", "name", "pathname", "process", "processName",
    "relativeCreated", "stack_info", "thread", "threadName", "taskName",
}


def configure_logging() -> None:
    level = getattr(logging, settings.app_log_level.upper(), logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    if settings.app_log_json:
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s %(levelname)-8s %(name)s: %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)

    # Dampen noisy libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
