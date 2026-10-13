"""Structured logging configuration for local and Cloud Run environments."""

import logging
import sys

from app.core.config import get_settings


def configure_logging() -> None:
    """Configure root logger for structured stdout output."""
    settings = get_settings()
    level = getattr(logging, settings.log_level.upper(), logging.INFO)

    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
        stream=sys.stdout,
        force=True,
    )
