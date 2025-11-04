"""
Celery Service for Lumina IQ RAG Backend.

Handles background task processing for document ingestion and batch operations.
"""

from typing import Dict, Any, Optional
from celery import Celery
from pathlib import Path
from config.settings import settings
from utils.logger import get_logger

logger = get_logger("celery_service")


class CeleryService:
    """Service for managing Celery background tasks."""

    def __init__(self):
        self.celery_app: Optional[Celery] = None
        self.is_initialized = False

    def initialize(self) -> None:
        """Initialize Celery application."""
        try:
            logger.info(
                "Initializing Celery service",
                extra={
                    "extra_fields": {
                        "broker": settings.CELERY_BROKER_URL.split("@")[-1],
                        "backend": settings.CELERY_RESULT_BACKEND.split("@")[-1],
                    }
                },
            )

            # Parse Redis URLs to add redis:// prefix if not present
            broker_url = settings.CELERY_BROKER_URL
            if "://" not in broker_url:
                broker_url = f"redis://{broker_url}"

            backend_url = settings.CELERY_RESULT_BACKEND
            if "://" not in backend_url:
                backend_url = f"redis://{backend_url}"

            # Initialize Celery app
            self.celery_app = Celery(
                "lumina_iq",
                broker=broker_url,
                backend=backend_url,
            )

            # Configure Celery
            self.celery_app.conf.update(
                task_serializer=settings.CELERY_TASK_SERIALIZER,
                result_serializer=settings.CELERY_RESULT_SERIALIZER,
                accept_content=["json"],
                timezone=settings.CELERY_TIMEZONE,
                enable_utc=settings.CELERY_ENABLE_UTC,
                task_track_started=True,
                task_time_limit=3600,  # 1 hour
                task_soft_time_limit=3300,  # 55 minutes
                worker_prefetch_multiplier=1,
                worker_max_tasks_per_child=100,
            )

            self.is_initialized = True
            logger.info("Celery service initialized successfully")

        except Exception as e:
            logger.error(
                f"Failed to initialize Celery service: {str(e)}",
                extra={"extra_fields": {"error_type": type(e).__name__}},
            )
            self.is_initialized = False
            # Don't raise - Celery is optional

    def create_task_ingest_document(self):
        """Create Celery task for document ingestion."""
        if not self.is_initialized or not self.celery_app:
            logger.warning("Celery service not initialized, cannot create tasks")
            return None

        @self.celery_app.task(name="tasks.ingest_document", bind=True)
        def ingest_document_task(self, file_path: str, metadata: Optional[Dict[str, Any]] = None):
            """Background task for document ingestion."""
            import asyncio
            from .rag_orchestrator import rag_orchestrator

            logger.info(
                f"Starting background document ingestion",
                extra={"extra_fields": {"file_path": file_path, "task_id": self.request.id}},
            )

            try:
                # Initialize orchestrator if needed
                if not rag_orchestrator.is_initialized:
                    rag_orchestrator.initialize()

                # Run ingestion
                result = asyncio.run(
                    rag_orchestrator.ingest_document(
                        file_path=Path(file_path),
                        metadata=metadata,
                    )
                )

                logger.info(
                    f"Background document ingestion completed",
                    extra={"extra_fields": {"file_path": file_path, "result": result}},
                )

                return result

            except Exception as e:
                logger.error(
                    f"Background document ingestion failed: {str(e)}",
                    extra={
                        "extra_fields": {
                            "error_type": type(e).__name__,
                            "file_path": file_path,
                        }
                    },
                )
                return {"success": False, "error": str(e)}

        return ingest_document_task

    def create_task_batch_embeddings(self):
        """Create Celery task for batch embedding generation."""
        if not self.is_initialized or not self.celery_app:
            logger.warning("Celery service not initialized, cannot create tasks")
            return None

        @self.celery_app.task(name="tasks.batch_embeddings", bind=True)
        def batch_embeddings_task(self, texts: list, cache: bool = True):
            """Background task for batch embedding generation."""
            import asyncio
            from .embedding_service import embedding_service

            logger.info(
                f"Starting background batch embedding generation",
                extra={"extra_fields": {"text_count": len(texts), "task_id": self.request.id}},
            )

            try:
                # Initialize service if needed
                if not embedding_service.is_initialized:
                    embedding_service.initialize()

                # Generate embeddings
                embeddings = asyncio.run(
                    embedding_service.generate_embeddings_batch(texts, use_cache=cache)
                )

                logger.info(
                    f"Background batch embedding generation completed",
                    extra={"extra_fields": {"text_count": len(texts), "embedding_count": len(embeddings)}},
                )

                return {"success": True, "embedding_count": len(embeddings)}

            except Exception as e:
                logger.error(
                    f"Background batch embedding generation failed: {str(e)}",
                    extra={
                        "extra_fields": {
                            "error_type": type(e).__name__,
                            "text_count": len(texts),
                        }
                    },
                )
                return {"success": False, "error": str(e)}

        return batch_embeddings_task

    def submit_ingest_document(
        self, file_path: str, metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """Submit document ingestion task to Celery."""
        if not self.is_initialized or not self.celery_app:
            logger.warning("Celery service not initialized, cannot submit tasks")
            return None

        try:
            task = self.celery_app.tasks.get("tasks.ingest_document")
            if not task:
                logger.error("Ingest document task not registered")
                return None

            result = task.apply_async(args=[file_path, metadata])

            logger.info(
                f"Submitted document ingestion task",
                extra={
                    "extra_fields": {
                        "file_path": file_path,
                        "task_id": result.id,
                    }
                },
            )

            return result.id

        except Exception as e:
            logger.error(
                f"Failed to submit document ingestion task: {str(e)}",
                extra={
                    "extra_fields": {
                        "error_type": type(e).__name__,
                        "file_path": file_path,
                    }
                },
            )
            return None

    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Get status of a Celery task."""
        if not self.is_initialized or not self.celery_app:
            return {"status": "unavailable", "error": "Celery service not initialized"}

        try:
            result = self.celery_app.AsyncResult(task_id)

            return {
                "task_id": task_id,
                "status": result.state,
                "result": result.result if result.ready() else None,
                "error": str(result.info) if result.failed() else None,
            }

        except Exception as e:
            logger.error(
                f"Failed to get task status: {str(e)}",
                extra={
                    "extra_fields": {
                        "error_type": type(e).__name__,
                        "task_id": task_id,
                    }
                },
            )
            return {"status": "error", "error": str(e)}


# Global singleton instance
celery_service = CeleryService()
