"""
Logging configuration and utilities.

Provides structured logging setup for the application.
"""

import logging
import sys
from typing import Optional

from app.core.config import settings


def setup_logging(level: str = None) -> None:
    """
    Configure application logging.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR).
    """
    log_level = level or ("DEBUG" if settings.DEBUG else "INFO")
    
    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Reduce noise from third-party libraries
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("sentence_transformers").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a module.
    
    Args:
        name: Logger name (typically __name__).
        
    Returns:
        Configured logger instance.
    """
    logger = logging.getLogger(name)
    return logger


class LoggerMixin:
    """
    Mixin class to add logging to any class.
    
    Usage:
        class MyService(LoggerMixin):
            def method(self):
                self.logger.info("Message")
    """
    
    @property
    def logger(self) -> logging.Logger:
        """Get logger for this class."""
        return get_logger(self.__class__.__name__)
