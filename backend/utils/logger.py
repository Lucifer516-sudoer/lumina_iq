import logging
from datetime import datetime
from pathlib import Path
import sys
from rich.logging import RichHandler
from rich.console import Console

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from config.settings import settings  # noqa: E402

# Prepare Console
console = Console()

# Map string to logging level (with fallback)
log_level_map = {
    "NOTSET": logging.NOTSET,
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}
log_level = log_level_map.get(
    getattr(settings, "LOG_LEVEL", "INFO").upper(), logging.INFO
)

app_logger = logging.getLogger("lumina_iq")
app_logger.setLevel(log_level)
app_logger.propagate = False
app_logger.handlers.clear()  # Use .clear() for clarity

# RichHandler (console, no custom formatter)
rich_handler = RichHandler(
    console=console, level=log_level, log_time_format="%b-%d-%Y %I:%M:%S %p"
)

# FileHandler (with formatter)
log_filename = f"{datetime.today().strftime('%d_%b_%Y')}.log"
file_handler = logging.FileHandler(filename=log_filename, encoding="utf-8", mode="a")
formatter = logging.Formatter(
    "%(asctime)s %(levelname)-8s %(message)s %(filename)s:%(lineno)d",
    datefmt="%b-%d-%Y %I:%M:%S %p",
)
file_handler.setFormatter(formatter)

# Attach handlers
app_logger.addHandler(rich_handler)
app_logger.addHandler(file_handler)

# Some convenience loggers for different modules
pdf_logger = app_logger.getChild("pdf_service")
cache_logger = app_logger.getChild("cache")
chat_logger = app_logger.getChild("chat_service")
ip_logger = app_logger.getChild("ip_detector")


# Convenience functions
def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for a specific module"""
    return app_logger.getChild(name)


def mutate_logger(name: str, level: int):
    """Mutate the log level of a specific logger"""
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(rich_handler)
    logger.addHandler(file_handler)
    return logger
