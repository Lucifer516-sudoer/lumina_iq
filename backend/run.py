#!/usr/bin/env python3
"""
Run script for the Learning App FastAPI backend.
This script starts the FastAPI server with uvicorn.
"""

import uvicorn
import sys
import os
import logging
import warnings

# Suppress Pydantic v2 warnings from dependencies
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic._internal._generate_schema")

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.settings import settings
from utils.ip_detector import setup_frontend_env
from utils.logger import app_logger, mutate_logger

logger = app_logger.getChild("run")


def setup_third_party_loggers():
    """
    Configure logging levels for third-party libraries to reduce noise.
    This ensures professional, context-rich logging without excessive verbosity.
    """
    try:
        # Map log level from settings
        log_level_map = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL,
        }
        app_log_level = log_level_map.get(settings.LOG_LEVEL.upper(), logging.INFO)
        
        # Set more restrictive levels for third-party libraries
        third_party_level = max(app_log_level, logging.WARNING)
        
        # Uvicorn loggers - keep at app level for important messages
        mutate_logger("uvicorn", app_log_level)
        mutate_logger("uvicorn.error", app_log_level)
        mutate_logger("uvicorn.access", logging.INFO)  # Access logs at INFO
        
        # Library loggers - reduce verbosity
        third_party_libs = [
            "urllib3",
            "qdrant_client",
            "llama_index",
            "httpx",
            "httpcore",
            "asyncio",
            "sqlalchemy",
            "multipart",
            "watchfiles",
            "openai",
            "together",
        ]
        
        for lib in third_party_libs:
            mutate_logger(lib, third_party_level)
        
        # FastAPI and Starlette - keep informative
        mutate_logger("fastapi", logging.INFO)
        mutate_logger("starlette", logging.INFO)
        
        logger.debug(
            "Third-party logger configuration complete",
            extra={
                "extra_fields": {
                    "app_level": settings.LOG_LEVEL,
                    "third_party_level": logging.getLevelName(third_party_level),
                }
            },
        )
    except Exception as e:
        logger.warning(
            f"Failed to configure some third-party loggers: {str(e)}",
            extra={"extra_fields": {"error_type": type(e).__name__}},
        )


def main():
    """Start the FastAPI server with professional logging and optimized configuration."""
    logger.info(
        "Starting Lumina IQ Backend",
        extra={
            "extra_fields": {
                "environment": settings.ENVIRONMENT,
                "host": settings.HOST,
                "port": settings.PORT,
                "log_level": settings.LOG_LEVEL,
            }
        },
    )

    # Configure third-party loggers to reduce noise
    setup_third_party_loggers()

    # Auto-detect IP and update frontend .env file
    try:
        detected_ip = setup_frontend_env(settings.PORT)
        logger.info(
            "Frontend environment configured",
            extra={
                "extra_fields": {
                    "detected_ip": detected_ip,
                    "port": settings.PORT,
                }
            },
        )
    except Exception as e:
        logger.warning(
            f"Failed to configure frontend environment: {str(e)}",
            extra={"extra_fields": {"error_type": type(e).__name__}},
        )
        detected_ip = settings.HOST

    # Log server configuration
    logger.info(
        "Server configuration",
        extra={
            "extra_fields": {
                "server_url": f"http://{settings.HOST}:{settings.PORT}",
                "accessible_url": f"http://{detected_ip}:{settings.PORT}",
                "books_directory": settings.BOOKS_DIR,
                "together_model": settings.TOGETHER_MODEL,
                "embedding_model": settings.EMBEDDING_MODEL,
                "qdrant_collection": settings.QDRANT_COLLECTION_NAME,
            }
        },
    )

    try:
        # Configure uvicorn with optimized settings and file watching exclusions
        uvicorn_config = uvicorn.Config(
            app="main:app",
            host=settings.HOST,
            port=settings.PORT,
            reload=True,
            reload_dirs=[
                os.path.dirname(os.path.abspath(__file__))
            ],  # Only watch backend dir
            reload_excludes=[
                "*.pyc",
                "__pycache__",
                ".git",
                "*.log",
                ".pytest_cache",
                "*.egg-info",
                "site-packages",  # Exclude site-packages
                ".venv",
                "venv",
                "env",
            ],
            log_level=settings.LOG_LEVEL.lower(),
            workers=1,  # Single worker for development with reload
            backlog=2048,
            timeout_keep_alive=5,
            limit_concurrency=settings.MAX_CONCURRENT_REQUESTS,
            use_colors=True,
        )

        server = uvicorn.Server(uvicorn_config)

        logger.info(
            "Server starting",
            extra={
                "extra_fields": {
                    "reload_enabled": True,
                    "workers": 1,
                    "max_concurrent": settings.MAX_CONCURRENT_REQUESTS,
                }
            },
        )

        server.run()

    except KeyboardInterrupt:
        logger.info(
            "Server stopped by user",
            extra={"extra_fields": {"reason": "keyboard_interrupt"}},
        )
    except Exception as e:
        logger.critical(
            f"Failed to start server: {str(e)}",
            extra={
                "extra_fields": {
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                }
            },
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
