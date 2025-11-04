"""
RAG Orchestrator for Lumina IQ Backend.

Coordinates all RAG services for end-to-end document processing and question generation.
"""

from typing import List, Dict, Any, Optional
from pathlib import Path
from llama_index.core import Document
from llama_index.core.schema import TextNode
from config.settings import settings
from utils.logger import get_logger
from .document_service import document_service
from .chunking_service import chunking_service
from .embedding_service import embedding_service
from .qdrant_service import qdrant_service
from .chat_service import chat_service
from .cache_service import cache_service

logger = get_logger("rag_orchestrator")


class RAGOrchestrator:
    """Orchestrator for RAG pipeline operations."""

    def __init__(self):
        self.is_initialized = False

    def initialize(self) -> None:
        """Initialize RAG orchestrator and all dependent services."""
        try:
            logger.info("Initializing RAG orchestrator")

            # Initialize all services
            document_service.initialize()
            chunking_service.initialize()
            embedding_service.initialize()
            qdrant_service.initialize()
            chat_service.initialize()

            self.is_initialized = True
            logger.info("RAG orchestrator initialized successfully")

        except Exception as e:
            logger.error(
                f"Failed to initialize RAG orchestrator: {str(e)}",
                extra={"extra_fields": {"error_type": type(e).__name__}},
            )
            self.is_initialized = False
            raise

    async def ingest_document(
        self, file_path: Path, metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Ingest a document into the RAG system."""
        if not self.is_initialized:
            raise RuntimeError("RAG orchestrator not initialized")

        try:
            logger.info(
                f"Ingesting document",
                extra={"extra_fields": {"file_path": str(file_path)}},
            )

            # Step 1: Validate document
            validation = await document_service.validate_document(file_path)
            if not validation["valid"]:
                logger.error(
                    f"Document validation failed: {validation.get('error')}",
                    extra={"extra_fields": {"file_path": str(file_path)}},
                )
                return {"success": False, "error": validation.get("error")}

            # Step 1.5: Check if document already exists
            file_hash = validation["file_hash"]
            logger.info(
                "Checking if document already exists",
                extra={"extra_fields": {"file_hash": file_hash[:8], "file_path": str(file_path)}},
            )
            
            document_exists = qdrant_service.check_document_exists(file_hash)
            
            if document_exists:
                logger.info(
                    "✓ Document already indexed - SKIPPING re-ingestion",
                    extra={"extra_fields": {"file_hash": file_hash[:8], "file_name": file_path.name}},
                )
                return {
                    "success": True,
                    "already_exists": True,
                    "file_name": file_path.name,
                    "file_hash": file_hash,
                    "message": "Document already indexed - skipped duplicate ingestion"
                }
            
            logger.info(
                "Document is new - proceeding with ingestion",
                extra={"extra_fields": {"file_hash": file_hash[:8], "file_name": file_path.name}},
            )

            # Step 2: Extract content from PDF
            documents = await document_service.extract_from_pdf(file_path)

            # Add custom metadata if provided
            if metadata:
                for doc in documents:
                    doc.metadata.update(metadata)

            # Step 3: Chunk documents
            nodes = await chunking_service.chunk_documents(documents)

            # Step 4: Generate embeddings for chunks
            texts = [node.text for node in nodes]
            embeddings = await embedding_service.generate_embeddings_batch(texts)

            # Step 5: Prepare metadata for Qdrant
            node_metadata = []
            for node in nodes:
                node_metadata.append(node.metadata)

            # Step 6: Store in Qdrant
            point_ids = await qdrant_service.upsert_points(
                texts=texts,
                embeddings=embeddings,
                metadata=node_metadata,
            )

            result = {
                "success": True,
                "file_name": file_path.name,
                "file_hash": validation["file_hash"],
                "page_count": len(documents),
                "chunk_count": len(nodes),
                "point_ids": point_ids[:5],  # Return first 5 IDs
            }

            logger.info(
                f"Successfully ingested document",
                extra={"extra_fields": result},
            )

            return result

        except Exception as e:
            logger.error(
                f"Failed to ingest document: {str(e)}",
                extra={
                    "extra_fields": {
                        "error_type": type(e).__name__,
                        "file_path": str(file_path),
                    }
                },
            )
            return {"success": False, "error": str(e)}

    async def query_and_generate(
        self,
        query: Optional[str] = None,
        count: int = 25,
        mode: str = "practice",
        top_k: int = 10,
        filter_conditions: Optional[Dict[str, Any]] = None,
        use_cache: bool = True,
    ) -> Dict[str, Any]:
        """Query documents and generate questions."""
        if not self.is_initialized:
            raise RuntimeError("RAG orchestrator not initialized")

        try:
            logger.info(
                "Executing query and generate pipeline",
                extra={
                    "extra_fields": {
                        "query": query,
                        "count": count,
                        "mode": mode,
                        "top_k": top_k,
                    }
                },
            )

            # Check cache if enabled
            if use_cache and settings.CACHE_QUERY_RESULTS:
                cache_key_params = {
                    "query": query or "all",
                    "count": count,
                    "mode": mode,
                    "top_k": top_k,
                    "filter": filter_conditions or {},
                }
                cached_response = await cache_service.get_cached_api_response(
                    "query_and_generate", cache_key_params
                )
                if cached_response:
                    logger.info("Returning cached query response")
                    return cached_response

            # Step 1: Retrieve relevant context
            context = await self.retrieve_context(
                query=query,
                top_k=top_k,
                filter_conditions=filter_conditions,
            )

            if not context:
                logger.warning("No context retrieved from documents")
                return {
                    "success": False,
                    "error": "No relevant context found in documents",
                }

            # Step 2: Generate response based on mode
            if mode == "chat":
                # Generate conversational chat response
                response_text = await chat_service.generate_chat_response(
                    query=query,
                    context=context,
                )
                logger.info(f"Successfully generated chat response - response_length: {len(response_text)}")
            else:
                # Generate questions for quiz/practice modes
                response_text = await chat_service.generate_questions(
                    context=context,
                    count=count,
                    mode=mode,
                    topic=query,
                )
                logger.info(f"Successfully generated questions - response_length: {len(response_text)}")

            result = {
                "success": True,
                "response": response_text,
                "context_length": len(context),
                "mode": mode,
                "count": count,
            }

            # Cache the response if enabled
            if use_cache and settings.CACHE_QUERY_RESULTS:
                await cache_service.cache_api_response(
                    "query_and_generate", cache_key_params, result
                )

            return result

        except Exception as e:
            logger.error(
                f"Failed to query and generate: {str(e)}",
                extra={
                    "extra_fields": {
                        "error_type": type(e).__name__,
                        "query": query,
                    }
                },
            )
            return {"success": False, "error": str(e)}

    async def retrieve_context(
        self,
        query: Optional[str] = None,
        top_k: int = 10,
        filter_conditions: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Retrieve relevant context from vector store."""
        try:
            logger.debug(
                "Retrieving context from vector store",
                extra={
                    "extra_fields": {
                        "query": query,
                        "top_k": top_k,
                        "has_filter": bool(filter_conditions),
                    }
                },
            )

            if query:
                # Generate query embedding
                query_embedding = await embedding_service.generate_embedding(query)

                # Search Qdrant
                results = await qdrant_service.search(
                    query_vector=query_embedding,
                    limit=top_k,
                    filter_conditions=filter_conditions,
                )
            else:
                # No query, get random documents
                scroll_result = qdrant_service.scroll_points(
                    filter_conditions=filter_conditions,
                    limit=top_k,
                )
                results = [
                    {"text": point["payload"].get("text", "")}
                    for point in scroll_result["points"]
                ]

            # Combine retrieved texts into context
            context_parts = [result["text"] for result in results if result.get("text")]
            context = "\n\n".join(context_parts)

            logger.debug(
                "Retrieved context successfully",
                extra={
                    "extra_fields": {
                        "result_count": len(results),
                        "context_length": len(context),
                    }
                },
            )

            return context

        except Exception as e:
            logger.error(
                f"Failed to retrieve context: {str(e)}",
                extra={
                    "extra_fields": {
                        "error_type": type(e).__name__,
                        "query": query,
                    }
                },
            )
            raise

    async def get_system_stats(self) -> Dict[str, Any]:
        """Get RAG system statistics."""
        try:
            # Get Qdrant stats
            collection_info = await qdrant_service.get_collection_info()

            # Get cache stats
            cache_stats = await cache_service.get_stats()

            return {
                "qdrant": collection_info,
                "cache": cache_stats,
                "services": {
                    "document_service": document_service.is_initialized,
                    "chunking_service": chunking_service.is_initialized,
                    "embedding_service": embedding_service.is_initialized,
                    "qdrant_service": qdrant_service.is_initialized,
                    "chat_service": chat_service.is_initialized,
                },
            }

        except Exception as e:
            logger.error(
                f"Failed to get system stats: {str(e)}",
                extra={"extra_fields": {"error_type": type(e).__name__}},
            )
            return {"error": str(e)}

    async def delete_document(
        self, file_hash: str
    ) -> Dict[str, Any]:
        """Delete a document from the system."""
        try:
            logger.info(
                f"Deleting document",
                extra={"extra_fields": {"file_hash": file_hash}},
            )

            # Delete from Qdrant
            result = await qdrant_service.delete_points({"file_hash": file_hash})

            logger.info(
                "Successfully deleted document",
                extra={"extra_fields": {"file_hash": file_hash}},
            )

            return {"success": True, "file_hash": file_hash}

        except Exception as e:
            logger.error(
                f"Failed to delete document: {str(e)}",
                extra={
                    "extra_fields": {
                        "error_type": type(e).__name__,
                        "file_hash": file_hash,
                    }
                },
            )
            return {"success": False, "error": str(e)}


# Global singleton instance
rag_orchestrator = RAGOrchestrator()
