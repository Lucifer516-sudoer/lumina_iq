"""
Enhanced logging configuration with Rich formatting, structured logging, and request ID support.
"""

import json
import logging
import os
import sys
import uuid
import threading
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import Optional

from config.settings import settings

# Suppress Google Cloud ALTS warnings at module level
os.environ["GRPC_VERBOSITY"] = "ERROR"
os.environ["GRPC_TRACE"] = ""

# Thread-local storage for request ID
_local = threading.local()

try:
    from rich.console import Console
    from rich.logging import RichHandler
    from rich.traceback import install
    from rich.theme import Theme

    RICH_AVAILABLE = True

    # Install rich traceback handler
    install(show_locals=False)

    # Custom theme for better readability
    custom_theme = Theme(
        {
            "info": "cyan",
            "warning": "yellow",
            "error": "bold red",
            "success": "bold green",
            "service": "bold blue",
            "timestamp": "dim white",
        }
    )

    console = Console(theme=custom_theme)

except ImportError:
    RICH_AVAILABLE = False
    console = None


class StructuredJSONFormatter(logging.Formatter):
    """Custom formatter for structured JSON logging with request ID support."""

    def format(self, record):
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add request ID if available
        request_id = getattr(_local, 'request_id', None)
        if request_id:
            log_entry["request_id"] = request_id

        # Add any additional fields from record
        if hasattr(record, 'extra_fields'):
            log_entry.update(record.extra_fields)

        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry, ensure_ascii=False)


class RequestIdFilter(logging.Filter):
    """Filter to add request ID to log records."""

    def filter(self, record):
        request_id = getattr(_local, 'request_id', None)
        if request_id:
            record.request_id = request_id
        return True


def set_request_id(request_id: Optional[str] = None) -> str:
    """Set the request ID for the current thread."""
    if request_id is None:
        request_id = str(uuid.uuid4())
    _local.request_id = request_id
    return request_id


def get_request_id() -> Optional[str]:
    """Get the current request ID."""
    return getattr(_local, 'request_id', None)


def clear_request_id():
    """Clear the request ID for the current thread."""
    if hasattr(_local, 'request_id'):
        delattr(_local, 'request_id')


def configure_logging():
    """Configure enhanced logging with Rich formatting and structured logging."""

    # Only configure logging once per process
    if hasattr(logging, "_configured_for_multiworker"):
        return

    # Suppress noisy loggers
    logging.getLogger("google.auth").setLevel(logging.WARNING)
    logging.getLogger("google.auth.transport").setLevel(logging.WARNING)
    logging.getLogger("google.auth._default").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("multipart").setLevel(logging.WARNING)

    # Get worker ID from environment
    worker_id = os.getenv("UVICORN_WORKER_ID", "1")

    # Get log level from settings
    log_level_str = settings.LOG_LEVEL.upper()

    # Map string to logging level
    log_level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }
    log_level = log_level_map.get(log_level_str, logging.INFO)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Add request ID filter to root logger
    root_logger.addFilter(RequestIdFilter())

    # Set up console handler for all workers to ensure logs are visible
    if RICH_AVAILABLE:
        # Use Rich handler for better formatting - no custom formatter needed
        rich_handler = RichHandler(
            console=console,
            show_time=False,
            show_path=False,
            show_level=False,
            rich_tracebacks=True,
        )
        console_handler = rich_handler
    else:
        # Fallback to standard handler
        console_handler = logging.StreamHandler()

    console_handler.setLevel(log_level)
    root_logger.addHandler(console_handler)

    # Set up file handler with TimedRotatingFileHandler for structured logging
    log_dir = Path(__file__).parent.parent / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "app.log"

    file_handler = TimedRotatingFileHandler(
        filename=str(log_file),
        when="midnight",
        interval=1,
        backupCount=7,
        encoding="utf-8",
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(StructuredJSONFormatter())
    root_logger.addHandler(file_handler)

    # Configure specific loggers to prevent spam
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(log_level)  # Use the same level as root

    # Mark as configured
    logging._configured_for_multiworker = True

    return worker_id


def get_logger(name: str):
    """Get a logger with enhanced configuration"""
    configure_logging()
    return logging.getLogger(name)


def log_performance(logger, operation: str, duration: float, extra_fields: Optional[dict] = None):
    """Log performance metrics with structured data."""
    log_data = {
        "operation": operation,
        "duration_ms": round(duration * 1000, 2),
        "performance": True
    }
    if extra_fields:
        log_data.update(extra_fields)

    logger.info(f"Performance: {operation} completed in {log_data['duration_ms']}ms", extra={"extra_fields": log_data})