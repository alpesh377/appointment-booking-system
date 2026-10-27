from __future__ import annotations

import logging
import sys

from app.core.config import settings


def configure_logging() -> None:
    """Send application logs to stdout in a predictable, parseable format."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(settings.log_level.upper())
    # Keep SQLAlchemy's engine logs out of the default output; opt in via LOG_LEVEL.
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
