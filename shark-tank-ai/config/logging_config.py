"""
Logging configuration for Shark Tank AI.

Uses Python's standard `logging.config.dictConfig` so behavior is
predictable and dependency-free. Call `setup_logging()` once, as early
as possible in the application's entry point (e.g. `app.py`), before
any other module logs anything.
"""

from __future__ import annotations

import logging
import logging.config
from pathlib import Path
from typing import Any, Dict

_CONFIGURED = False


def build_logging_config(
    log_level: str = "INFO",
    log_to_file: bool = False,
    log_file_path: str = "logs/app.log",
) -> Dict[str, Any]:
    """Build a dictConfig-compatible logging configuration dict."""

    handlers: Dict[str, Any] = {
        "console": {
            "class": "logging.StreamHandler",
            "level": log_level,
            "formatter": "standard",
            "stream": "ext://sys.stdout",
        }
    }
    root_handlers = ["console"]

    if log_to_file:
        Path(log_file_path).parent.mkdir(parents=True, exist_ok=True)
        handlers["file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "level": log_level,
            "formatter": "standard",
            "filename": log_file_path,
            "maxBytes": 5 * 1024 * 1024,  # 5 MB
            "backupCount": 3,
            "encoding": "utf-8",
        }
        root_handlers.append("file")

    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        "handlers": handlers,
        "root": {
            "level": log_level,
            "handlers": root_handlers,
        },
        "loggers": {
            # Quiet down noisy third-party libraries by default.
            "urllib3": {"level": "WARNING", "propagate": True},
            "httpx": {"level": "WARNING", "propagate": True},
            "watchdog": {"level": "WARNING", "propagate": True},
        },
    }


def setup_logging(
    log_level: str = "INFO",
    log_to_file: bool = False,
    log_file_path: str = "logs/app.log",
    force: bool = False,
) -> None:
    """Configure application-wide logging.

    Safe to call multiple times; configuration is only applied once
    unless `force=True` (useful in tests).
    """
    global _CONFIGURED
    if _CONFIGURED and not force:
        return

    config = build_logging_config(
        log_level=log_level.upper(),
        log_to_file=log_to_file,
        log_file_path=log_file_path,
    )
    logging.config.dictConfig(config)
    _CONFIGURED = True

    logger = logging.getLogger(__name__)
    logger.debug("Logging configured (level=%s, log_to_file=%s)", log_level, log_to_file)


def get_logger(name: str) -> logging.Logger:
    """Convenience wrapper around `logging.getLogger`.

    Ensures logging has been configured with sane defaults if the
    caller forgot to invoke `setup_logging()` first.
    """
    if not _CONFIGURED:
        setup_logging()
    return logging.getLogger(name)
