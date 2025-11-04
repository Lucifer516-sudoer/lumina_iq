"""
Services package for Lumina IQ RAG Backend.

This package contains all service modules for document processing, embedding generation,
vector storage, caching, and RAG orchestration.

Architecture:
- auth_service: Authentication and session management
- document_service: PDF extraction and preprocessing using LlamaIndex
- chunking_service: Text chunking using LlamaIndex
- embedding_service: Embedding generation using LangChain + Together AI
- qdrant_service: Vector database operations
- cache_service: Redis-based caching
- together_service: Together AI API integration
- chat_service: Chat and question generation using LangChain
- pdf_service: PDF operations and management
- health_service: System health monitoring and checks
- rag_orchestrator: Main RAG pipeline coordinator
- celery_service: Background task processing
"""

from .auth_service import auth_service
from .cache_service import cache_service
from .qdrant_service import qdrant_service
from .embedding_service import embedding_service
from .together_service import together_service
from .document_service import document_service
from .chunking_service import chunking_service
from .chat_service import chat_service
from .pdf_service import PDFService
from .health_service import health_service
from .rag_orchestrator import rag_orchestrator
from .celery_service import celery_service

__all__ = [
    "auth_service",
    "cache_service",
    "qdrant_service",
    "embedding_service",
    "together_service",
    "document_service",
    "chunking_service",
    "chat_service",
    "PDFService",
    "health_service",
    "rag_orchestrator",
    "celery_service",
]
