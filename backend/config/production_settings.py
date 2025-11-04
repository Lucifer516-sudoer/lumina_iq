"""
Production Settings - Simplified Single .env Configuration
===========================================================
Loads all configuration from a single .env file in the project root.
No environment-specific files needed - use environment variables to override.
"""

from pathlib import Path
from typing import List, Optional
from pydantic import Field, computed_field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ProductionSettings(BaseSettings):
    """
    Single source of truth for all application configuration.
    Loads from .env file in backend directory.
    """
    
    model_config = SettingsConfigDict(
        # Single .env file location
        env_file=str(Path(__file__).parent.parent / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )
    
    # ==================================================================================
    # CORE ENVIRONMENT
    # ==================================================================================
    
    ENVIRONMENT: str = Field(default="development", description="Environment: development, staging, production")
    SERVICE_NAME: str = Field(default="lumina_iq", description="Service name for logging and monitoring")
    
    # ==================================================================================
    # SERVER CONFIGURATION
    # ==================================================================================
    
    HOST: str = Field(default="0.0.0.0")
    PORT: int = Field(default=8000)
    
    @field_validator('CORS_ORIGINS', mode='before')
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS origins from string or list"""
        if isinstance(v, str):
            # Handle JSON string format
            import json
            try:
                return json.loads(v)
            except:
                # Handle comma-separated format
                return [origin.strip() for origin in v.split(',') if origin.strip()]
        return v or ["*"]
    
    CORS_ORIGINS: List[str] = Field(default=["*"])
    
    # ==================================================================================
    # AI PROVIDERS
    # ==================================================================================
    
    # Together.ai (Primary AI Provider)
    TOGETHER_API_KEY: str = Field(default="", description="Together.ai API key")
    TOGETHER_MODEL: str = Field(default="meta-llama/Llama-3.3-70B-Instruct-Turbo", description="Together.ai model")
    TOGETHER_BASE_URL: str = Field(default="https://api.together.xyz/v1")
    
    # Google Gemini (Fallback AI Provider)
    GEMINI_API_KEY: str = Field(default="", description="Primary Gemini API key")
    GEMINI_MODEL: str = Field(default="gemini-2.0-flash-exp")
    
    # Multiple Gemini keys for load balancing
    GEMINI_API_KEY_1: Optional[str] = Field(default=None)
    GEMINI_API_KEY_2: Optional[str] = Field(default=None)
    GEMINI_API_KEY_3: Optional[str] = Field(default=None)
    GEMINI_API_KEY_4: Optional[str] = Field(default=None)
    
    @computed_field
    @property
    def GEMINI_API_KEYS(self) -> List[str]:
        """Collect all configured Gemini API keys"""
        keys = []
        if self.GEMINI_API_KEY:
            keys.append(self.GEMINI_API_KEY)
        for i in range(1, 5):
            key = getattr(self, f'GEMINI_API_KEY_{i}', None)
            if key:
                keys.append(key)
        return keys
    
    # ==================================================================================
    # RAG CONFIGURATION
    # ==================================================================================
    
    # Embedding Configuration
    EMBEDDING_MODEL: str = Field(default="BAAI/bge-large-en-v1.5")
    EMBEDDING_DIMENSIONS: int = Field(default=1024)
    EMBEDDING_BATCH_SIZE: int = Field(default=32, description="Batch size for embedding generation")
    
    # Qdrant Vector Store
    QDRANT_URL: str = Field(default="http://localhost:6333")
    QDRANT_API_KEY: str = Field(default="")
    QDRANT_COLLECTION_NAME: str = Field(default="lumina_iq_documents")
    QDRANT_USE_HYBRID_SEARCH: bool = Field(default=True)
    
    # Chunking Configuration
    CHUNK_SIZE: int = Field(default=256, description="Chunk size for text splitting")
    CHUNK_OVERLAP: int = Field(default=50, description="Overlap between chunks")
    
    # Retrieval Configuration
    RETRIEVAL_TOP_K: int = Field(default=10, description="Number of chunks to retrieve")
    RETRIEVAL_SIMILARITY_THRESHOLD: float = Field(default=0.7, description="Minimum similarity score")
    RERANKING_ENABLED: bool = Field(default=True, description="Enable reranking of retrieved chunks")
    
    # ==================================================================================
    # CACHING & PERFORMANCE
    # ==================================================================================
    
    # Redis Configuration
    REDIS_URL: str = Field(default="redis://localhost:6379")
    REDIS_CACHE_DB: int = Field(default=0)
    REDIS_TASK_DB: int = Field(default=1)
    
    # Cache Settings
    CACHE_EMBEDDINGS: bool = Field(default=True)
    CACHE_QUERY_RESULTS: bool = Field(default=True)
    CACHE_TTL_SECONDS: int = Field(default=3600)
    
    # Performance Limits
    MAX_WORKERS: int = Field(default=4)
    MAX_CONCURRENT_REQUESTS: int = Field(default=100)
    
    # ==================================================================================
    # CELERY (ASYNC TASKS)
    # ==================================================================================
    
    CELERY_BROKER_URL: str = Field(default="redis://localhost:6379/1")
    CELERY_RESULT_BACKEND: str = Field(default="redis://localhost:6379/2")
    CELERY_TASK_SERIALIZER: str = Field(default="json")
    CELERY_RESULT_SERIALIZER: str = Field(default="json")
    CELERY_ACCEPT_CONTENT: List[str] = Field(default=["json"])
    CELERY_TIMEZONE: str = Field(default="UTC")
    CELERY_ENABLE_UTC: bool = Field(default=True)
    
    # ==================================================================================
    # LOGGING & MONITORING
    # ==================================================================================
    
    LOG_LEVEL: str = Field(default="INFO", description="Logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL")
    LOG_FORMAT: str = Field(default="json", description="Log format: json, text")
    LOG_DIR: str = Field(default="logs")
    
    # Monitoring
    ENABLE_PROMETHEUS_METRICS: bool = Field(default=False)
    METRICS_PORT: int = Field(default=9090)
    
    # ==================================================================================
    # SECURITY
    # ==================================================================================
    
    # Authentication
    LOGIN_USERNAME: str = Field(default="admin")
    LOGIN_PASSWORD: str = Field(default="password")
    
    # JWT & Encryption
    JWT_SECRET: str = Field(default="change-this-in-production", description="JWT secret key")
    ENCRYPTION_KEY: str = Field(default="change-this-in-production", description="Encryption key")
    SESSION_EXPIRE_HOURS: int = Field(default=24)
    
    # ==================================================================================
    # FILE STORAGE
    # ==================================================================================
    
    BOOKS_DIR: str = Field(default="./books")
    CACHE_DIR: str = Field(default="./cache")
    
    # ==================================================================================
    # GUNICORN (PRODUCTION SERVER)
    # ==================================================================================
    
    GUNICORN_WORKERS: int = Field(default=4)
    GUNICORN_THREADS: int = Field(default=2)
    GUNICORN_WORKER_TIMEOUT: int = Field(default=30)
    GUNICORN_MAX_REQUESTS: int = Field(default=10000)
    GUNICORN_MAX_REQUESTS_JITTER: int = Field(default=1000)
    
    # ==================================================================================
    # HEALTH CHECKS
    # ==================================================================================
    
    HEALTH_CHECK_INTERVAL: int = Field(default=30)
    HEALTH_CHECK_TIMEOUT: int = Field(default=10)
    HEALTH_CHECK_RETRIES: int = Field(default=3)
    
    # ==================================================================================
    # CIRCUIT BREAKER
    # ==================================================================================
    
    CIRCUIT_BREAKER_FAILURE_THRESHOLD: int = Field(default=5)
    CIRCUIT_BREAKER_RECOVERY_TIMEOUT: int = Field(default=60)
    
    # ==================================================================================
    # RATE LIMITING
    # ==================================================================================
    
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = Field(default=1000)
    RATE_LIMIT_BURST_SIZE: int = Field(default=100)
    
    # ==================================================================================
    # EXTERNAL SERVICES
    # ==================================================================================
    
    # LangChain (Optional)
    LANGCHAIN_TRACING_V2: bool = Field(default=False)
    LANGCHAIN_ENDPOINT: str = Field(default="https://api.smith.langchain.com")
    LANGCHAIN_API_KEY: str = Field(default="")
    LANGCHAIN_PROJECT: str = Field(default="lumina_iq")
    
    # Database (Optional)
    DATABASE_URL: str = Field(default="")
    DATABASE_POOL_SIZE: int = Field(default=20)
    DATABASE_MAX_OVERFLOW: int = Field(default=30)
    
    # Telegram (Optional)
    TELEGRAM_BOT_TOKEN: str = Field(default="")
    
    # ==================================================================================
    # COMPUTED PROPERTIES
    # ==================================================================================
    
    @computed_field
    @property
    def IS_PRODUCTION(self) -> bool:
        """Check if running in production"""
        return self.ENVIRONMENT.lower() == "production"
    
    @computed_field
    @property
    def IS_DEVELOPMENT(self) -> bool:
        """Check if running in development"""
        return self.ENVIRONMENT.lower() == "development"
    
    @computed_field
    @property
    def LOG_JSON_FORMAT(self) -> bool:
        """Whether to use JSON log format"""
        return self.LOG_FORMAT.lower() == "json"


# Global settings instance
settings = ProductionSettings()


# Export settings
__all__ = ['settings', 'ProductionSettings']
