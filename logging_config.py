"""
logging_config.py — Structured JSON Logging with Correlation ID support

Usage:
    from logging_config import configure_logging
    configure_logging()           # call once at app startup

    import logging
    logger = logging.getLogger(__name__)
    logger.info("event_name", extra={"key": "value", "request_id": req_id})

All log records are emitted as single-line JSON to stdout, compatible with
CloudWatch, Datadog, Google Cloud Logging, and any structured log aggregator.
"""

import logging
import sys
import os
from pythonjsonlogger.json import JsonFormatter


class CorrelationFilter(logging.Filter):
    """Injects request_id='-' when no correlation context is set."""

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "request_id"):
            record.request_id = "-"
        if not hasattr(record, "tenant_id"):
            record.tenant_id = "-"
        return True


def configure_logging(level: int = logging.INFO) -> None:
    """
    Configure the root logger with a JSON formatter.

    Call this exactly once at application startup (before any other logging).
    Subsequent calls are no-ops if handlers are already attached.
    """
    root = logging.getLogger()

    # Idempotent — don't add duplicate handlers on reload
    if root.handlers:
        return

    root.setLevel(level)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)

    fmt = JsonFormatter(
        fmt="%(asctime)s %(name)s %(levelname)s %(message)s %(request_id)s %(tenant_id)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
        rename_fields={"asctime": "timestamp", "name": "logger", "levelname": "level"},
    )
    handler.setFormatter(fmt)
    handler.addFilter(CorrelationFilter())

    root.addHandler(handler)

    # Quieten noisy third-party loggers
    for noisy in ("httpx", "httpcore", "urllib3", "chromadb", "langchain", "openai"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    logging.info(
        "logging_configured",
        extra={"level": logging.getLevelName(level), "format": "json"},
    )
