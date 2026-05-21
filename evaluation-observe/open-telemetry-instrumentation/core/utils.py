"""Utility functions for the Bedrock Agent instrumentation."""

import functools
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def dont_throw(func):
    """Decorator to catch exceptions and log them without raising."""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.warning(f"Exception caught in {func.__name__}: {e}")
            logger.debug(f"Exception details:", exc_info=True)

    return wrapper