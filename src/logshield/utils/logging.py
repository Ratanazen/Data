"""
Structured Logging utility for LogShield
"""

import json
import logging
import os
import sys
from datetime import datetime, timezone


class JSONFormatter(logging.Formatter):
    """Formats log records as structured single-line JSON."""
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "component": record.name,
            "message": record.getMessage(),
        }
        if hasattr(record, "extra") and isinstance(record.extra, dict):
            payload.update(record.extra)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload)

def setup_logger(name: str = "logshield", level: str = None) -> logging.Logger:
    """Configures and returns a structured logger."""
    log_level_str = (level or os.getenv("LOG_LEVEL", "INFO")).upper()
    log_level = getattr(logging, log_level_str, logging.INFO)

    logger = logging.getLogger(name)
    logger.setLevel(log_level)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(log_level)
        # Use structured JSON in production/staging, friendly format in dev
        app_env = os.getenv("APP_ENV", "development").lower()
        if app_env in ("production", "staging"):
            handler.setFormatter(JSONFormatter())
        else:
            handler.setFormatter(
                logging.Formatter("[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s", datefmt="%H:%M:%S")
            )
        logger.addHandler(handler)

    return logger

def get_logger(name: str = "logshield", level: str = None) -> logging.Logger:
    """Configures and returns a named structured logger."""
    return setup_logger(name, level)

logger = setup_logger("logshield")

