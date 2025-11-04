import socket
import os
from pathlib import Path
from typing import List, Optional

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


def get_local_ip() -> str:
    """Get the local IP address for CORS configuration."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"


class Settings(BaseSettings):
    # Environment-based configuration loading
    @property
    def env_file_path(self) -> str:
        """Get environment-specific .env file path."""
        env = os.getenv("ENVIRONMENT", "development")
        env_file_map = {
            "development": ".env",
            "staging": ".env.staging",
            "production": ".env.production",
        }
        env_file = env_file_map.get(env, ".env")
        return str(Path(__file__).parent.parent / env_file)

    model_config = SettingsConfigDict(
        env_file=".env",  # Will be set dynamically
        env_file_encoding="utf-8",
        extra="ignore",  # For backwards compatibility with pydantic 1.x
    )

    # Environment
    ENVIRONMENT: str = Field(default="development")

    # Authentication
    LOGIN_USERNAME: str = Field(default="admin")
    LOGIN_PASSWORD: str = Field(default="password")

    # Gemini AI
    GEMINI_API_KEY: str = Field(default="AIzaSyBiKBADQGhRuFn5glEU-frmORFc0KRleVQ")
    GEMINI_MODEL: str = Field(default="gemini-2.0-flash-lite")

    # Together.ai Configuration
    TOGETHER_API_KEY: str = Field(default="")
    TOGETHER_MODEL: str = Field(default="openai/gpt-oss-20b")
    TOGETHER_BASE_URL: str = Field(default="https://api.together.xyz/v1")

    # Embedding Configuration
    EMBEDDING_MODEL: str = Field(default="togethercomputer/m2-bert-80M-32k-retrieval")
    EMBEDDING_DIMENSIONS: int = Field(default=768)

    # LlamaIndex Configuration - Optimized for 32k context embedding model
    LLAMAINDEX_CHUNK_SIZE: int = Field(default=2048)  # Larger chunks for better semantic coherence
    LLAMAINDEX_CHUNK_OVERLAP: int = Field(default=256)  # Proportional overlap ~12.5%
    LLAMAINDEX_USE_FOR_LARGE_PDFS: bool = Field(default=True)
    LLAMAINDEX_LARGE_PDF_THRESHOLD_MB: int = Field(default=10)

    # Qdrant Cloud Configuration
    QDRANT_URL: str = Field(
        default="https://1f6b3bbc-d09e-40c2-b333-0a823825f876.europe-west3-0.gcp.cloud.qdrant.io:6333"
    )  # i Know this is the worst possible way to actually handle api keys but im in a rush, can fix later i suppose :} -\_(ツ)_/-
    QDRANT_API_KEY: str = Field(
        default="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.O8xNwnZuHGOxo1dcIdcgKrRVZGryxKPYyGaCVyNXziQ"
    )
    @computed_field
    @property
    def QDRANT_COLLECTION_NAME(self) -> str:
        """Generate environment-specific collection name for Qdrant"""
        base_name = "lumina_iq_documents"
        env_suffixes = {
            "development": "_dev",
            "staging": "_staging",
            "production": "_prod"
        }
        suffix = env_suffixes.get(self.ENVIRONMENT, "_dev")  # Default to dev if unknown
        return f"{base_name}{suffix}"
    QDRANT_USE_HYBRID_SEARCH: bool = Field(
        default=True
    )  # Enable hybrid search for better recall

    # CORS - Dynamic IP detection for development
    @property
    def CORS_ORIGINS(self) -> List[str]:
        local_ip = get_local_ip()
        origins = [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:3001",
            "http://127.0.0.1:3001",
            f"http://{local_ip}:3000",
            f"http://{local_ip}:3001",
            "*",
        ]
        return list(set(origins))  # Remove duplicates

    # File paths - Use relative paths from project root
    @property
    def BOOKS_DIR(self) -> str:
        # Get the project root directory (parent of backend)
        backend_dir = Path(__file__).parent.parent
        project_root = backend_dir.parent
        books_dir = project_root / "books"
        return str(books_dir)

    CACHE_DIR: str = Field(default="cache")

    # Session
    SESSION_EXPIRE_HOURS: int = Field(default=24)

    # Server
    HOST: str = Field(default="0.0.0.0")
    PORT: int = Field(default=8000)

    # Performance Settings for Render Free Tier (512MB RAM, 1 CPU core)
    MAX_WORKERS: int = Field(default=1)  # Single-threaded for 1 CPU core
    MAX_CONCURRENT_REQUESTS: int = Field(
        default=10
    )  # Reduced to prevent memory overload
    EMBEDDING_BATCH_SIZE: int = Field(
        default=50, description="Batch size for embedding generation (optimized for 32k context model)"
    )
    CACHE_EMBEDDINGS: bool = Field(default=True)  # Enable caching for embeddings
    CACHE_QUERY_RESULTS: bool = Field(default=True)  # Enable caching for query results
    CACHE_TTL_SECONDS: int = Field(default=3600)  # 1 hour cache TTL
    LOG_LEVEL: str = Field(default="DEBUG")  # Logging level

    # Redis Configuration for Production Caching
    REDIS_URL: str = Field(default="redis://localhost:6379")
    REDIS_CACHE_DB: int = Field(default=0)  # Database for caching
    REDIS_TASK_DB: int = Field(default=1)  # Database for Celery tasks

    # Celery Configuration
    CELERY_BROKER_URL: str = Field(default="redis://localhost:6379/1")
    CELERY_RESULT_BACKEND: str = Field(default="redis://localhost:6379/2")
    CELERY_TASK_SERIALIZER: str = Field(default="json")
    CELERY_RESULT_SERIALIZER: str = Field(default="json")
    CELERY_ACCEPT_CONTENT: List[str] = Field(default=["json"])
    CELERY_TIMEZONE: str = Field(default="UTC")
    CELERY_ENABLE_UTC: bool = Field(default=True)

    # Circuit Breaker Configuration
    CIRCUIT_BREAKER_FAILURE_THRESHOLD: int = Field(default=5)
    CIRCUIT_BREAKER_RECOVERY_TIMEOUT: int = Field(default=60)
    CIRCUIT_BREAKER_EXPECTED_EXCEPTION: str = Field(default="Exception")

    # LangChain Configuration
    LANGCHAIN_TRACING_V2: bool = Field(default=False)
    LANGCHAIN_ENDPOINT: str = Field(default="https://api.smith.langchain.com")
    LANGCHAIN_API_KEY: str = Field(default="")
    LANGCHAIN_PROJECT: str = Field(default="production_lumina_iq")

    # Rate Limiting Configuration
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = Field(default=1000)
    RATE_LIMIT_BURST_SIZE: int = Field(default=100)

    # Database Configuration
    DATABASE_URL: str = Field(default="")
    DATABASE_POOL_SIZE: int = Field(default=20)
    DATABASE_MAX_OVERFLOW: int = Field(default=30)

    # External Services
    TELEGRAM_BOT_TOKEN: str = Field(default="")

    # Advanced LlamaIndex Configuration
    LLAMAINDEX_SIMILARITY_TOP_K: int = Field(default=10)
    LLAMAINDEX_SIMILARITY_CUTOFF: float = Field(default=0.0)
    LLAMAINDEX_NODE_POSTPROCESSORS: List[str] = Field(default_factory=list)

    # Production scaling settings
    GUNICORN_WORKERS: int = Field(default=4)
    GUNICORN_THREADS: int = Field(default=4)
    GUNICORN_WORKER_TIMEOUT: int = Field(default=30)
    GUNICORN_MAX_REQUESTS: int = Field(default=1000)
    GUNICORN_MAX_REQUESTS_JITTER: int = Field(default=50)

    # Health check settings
    HEALTH_CHECK_INTERVAL: int = Field(default=30)
    HEALTH_CHECK_TIMEOUT: int = Field(default=10)
    HEALTH_CHECK_RETRIES: int = Field(default=3)

    # Monitoring and observability
    ENABLE_PROMETHEUS_METRICS: bool = Field(default=False)
    METRICS_PORT: int = Field(default=9090)

    # Graceful shutdown settings
    SHUTDOWN_TIMEOUT: int = Field(default=30)
    WORKER_SHUTDOWN_TIMEOUT: int = Field(default=25)


# Initialize settings with dynamic env file loading
settings = Settings()

# Manually load the environment file after initialization to handle dynamic paths
from dotenv import load_dotenv

load_dotenv(settings.env_file_path, override=True)

# Reinitialize settings with loaded environment variables
settings = Settings()
