from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import time
import os
import platform

# Import warning suppression first

from config.settings import settings
from routes import auth, pdf, chat, health
from utils.logger import get_logger
from utils.logging_config import log_performance
from utils.nltk_init import initialize_nltk_data
import asyncio

# Initialize services
from services.auth_service import auth_service
from services.cache_service import cache_service
from services.celery_service import celery_service
from services.rag_orchestrator import rag_orchestrator
from services.together_service import together_service

# Windows-compatible async optimizations
if platform.system() == "Windows":
    # Use ProactorEventLoop for better Windows performance
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
else:
    # Try uvloop on Unix systems
    try:
        import uvloop  # type: ignore

        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    except ImportError:
        pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    startup_start = time.time()
    logger = get_logger("main")

    # Log version and environment information
    logger.info(
        "Starting Learning App API",
        extra={
            "extra_fields": {
                # "version": settings.VERSION,
                "version": "0.0.9",
                "environment": os.getenv("ENVIRONMENT", "development"),
                "platform": platform.platform(),
                "python_version": platform.python_version(),
                "workers": os.getenv("WEB_CONCURRENCY", "1"),
            }
        },
    )

    # Initialize authentication service (non-critical but recommended)
    auth_start = time.time()
    logger.info("Initializing authentication service...")
    auth_initialized = False
    try:
        auth_service.initialize()
        auth_duration = time.time() - auth_start
        auth_initialized = True
        log_performance(logger, "auth_initialization", auth_duration)
        logger.info("Authentication service initialized successfully")
    except Exception as e:
        auth_duration = time.time() - auth_start
        logger.error(
            f"Failed to initialize authentication service: {str(e)}",
            extra={
                "extra_fields": {
                    "error_type": type(e).__name__,
                    "duration_ms": round(auth_duration * 1000, 2),
                }
            },
        )
        logger.warning("Authentication features will be limited")

    # Initialize NLTK data (critical for text processing)
    nltk_start = time.time()
    logger.info("Initializing NLTK data...")
    try:
        initialize_nltk_data()
        nltk_duration = time.time() - nltk_start
        log_performance(logger, "nltk_initialization", nltk_duration)
        logger.info("NLTK data initialized successfully")
    except Exception as e:
        nltk_duration = time.time() - nltk_start
        logger.error(
            f"Failed to initialize NLTK data: {str(e)}",
            extra={
                "extra_fields": {
                    "error_type": type(e).__name__,
                    "duration_ms": round(nltk_duration * 1000, 2),
                }
            },
        )
        logger.warning("Application may experience issues with text processing")
        # Continue startup - NLTK is important but not critical for basic functionality

    # Initialize cache service (critical for performance)
    cache_start = time.time()
    logger.info("Initializing cache service...")
    cache_initialized = False
    try:
        await cache_service.initialize()
        cache_duration = time.time() - cache_start
        cache_initialized = True
        log_performance(logger, "cache_initialization", cache_duration)
        logger.info("Cache service initialized successfully")
    except Exception as e:
        cache_duration = time.time() - cache_start
        logger.error(
            f"Failed to initialize cache service: {str(e)}",
            extra={
                "extra_fields": {
                    "error_type": type(e).__name__,
                    "duration_ms": round(cache_duration * 1000, 2),
                }
            },
        )
        logger.warning(
            "Application will continue without caching - performance may be degraded"
        )
        # Continue without cache - it's not critical for basic functionality

    # Initialize Together AI service (critical for AI features)
    together_start = time.time()
    logger.info("Initializing Together AI service...")
    together_initialized = False
    try:
        together_service.initialize()
        together_duration = time.time() - together_start
        together_initialized = True
        log_performance(logger, "together_initialization", together_duration)
        logger.info("Together AI service initialized successfully")
    except Exception as e:
        together_duration = time.time() - together_start
        logger.error(
            f"Failed to initialize Together AI service: {str(e)}",
            extra={
                "extra_fields": {
                    "error_type": type(e).__name__,
                    "duration_ms": round(together_duration * 1000, 2),
                }
            },
        )
        logger.warning("AI features will be limited")

    # Initialize RAG orchestrator (critical for RAG pipeline)
    rag_start = time.time()
    logger.info("Initializing RAG orchestrator...")
    rag_initialized = False
    try:
        rag_orchestrator.initialize()
        rag_duration = time.time() - rag_start
        rag_initialized = True
        log_performance(logger, "rag_initialization", rag_duration)
        logger.info("RAG orchestrator initialized successfully")
    except Exception as e:
        rag_duration = time.time() - rag_start
        logger.error(
            f"Failed to initialize RAG orchestrator: {str(e)}",
            extra={
                "extra_fields": {
                    "error_type": type(e).__name__,
                    "duration_ms": round(rag_duration * 1000, 2),
                }
            },
        )
        logger.warning("RAG features will be unavailable")

    # Initialize Celery service (non-critical - background tasks)
    celery_start = time.time()
    logger.info("Initializing Celery service...")
    celery_initialized = False
    try:
        celery_service.initialize()
        celery_duration = time.time() - celery_start
        celery_initialized = True
        log_performance(logger, "celery_initialization", celery_duration)
        logger.info("Celery service initialized successfully")
    except Exception as e:
        celery_duration = time.time() - celery_start
        logger.error(
            f"Failed to initialize Celery service: {str(e)}",
            extra={
                "extra_fields": {
                    "error_type": type(e).__name__,
                    "duration_ms": round(celery_duration * 1000, 2),
                }
            },
        )
        logger.warning("Background task processing will be unavailable")

    # Calculate total startup time
    total_startup_time = time.time() - startup_start

    # Log initialization summary with performance metrics
    initialized_services = []
    failed_services = []

    if "nltk" in globals() or True:  # NLTK is always attempted
        try:
            import nltk

            initialized_services.append("NLTK")
        except:
            failed_services.append("NLTK")

    if auth_initialized:
        initialized_services.append("Authentication")
    else:
        failed_services.append("Authentication")

    if cache_initialized:
        initialized_services.append("Cache")
    else:
        failed_services.append("Cache")

    if together_initialized:
        initialized_services.append("Together AI")
    else:
        failed_services.append("Together AI")

    if rag_initialized:
        initialized_services.append("RAG Orchestrator")
    else:
        failed_services.append("RAG Orchestrator")

    if celery_initialized:
        initialized_services.append("Celery")
    else:
        failed_services.append("Celery")

    logger.info(
        "Service initialization complete",
        extra={
            "extra_fields": {
                "initialized_services": initialized_services,
                "failed_services": failed_services,
                "total_startup_time_ms": round(total_startup_time * 1000, 2),
                "ready_for_requests": True,
            }
        },
    )

    if failed_services:
        logger.warning(f"Failed services detected: {', '.join(failed_services)}")

    yield
    # Shutdown
    logger.debug("Shutting down Learning App API...")

    # Gracefully shut down services
    if cache_initialized:
        try:
            await cache_service.close()
            logger.info("Cache service closed successfully")
        except Exception as e:
            logger.error(
                f"Error closing cache service: {str(e)}",
                extra={"extra_fields": {"error_type": type(e).__name__}},
            )


app = FastAPI(
    title="Learning App API",
    # version=settings.VERSION,
    version="0.9.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(pdf.router)
app.include_router(chat.router)
app.include_router(health.router)


# Health check endpoint (legacy - now handled by health router)
@app.get("/")
async def root():
    return {"message": "Learning App API is running"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=settings.HOST,
        port=settings.PORT,
        workers=1,  # Use 1 worker for development, increase for production
        loop="asyncio",  # Use asyncio (Windows compatible)
        access_log=True,
        log_level="debug",
        # Windows-compatible performance settings
        backlog=2048,
        timeout_keep_alive=5,
    )
