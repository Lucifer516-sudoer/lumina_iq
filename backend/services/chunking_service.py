"""
Chunking Service for Lumina IQ RAG Backend.

Handles text chunking using LlamaIndex with configurable strategies.
"""

from typing import List, Dict, Any, Optional
from llama_index.core import Document
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.schema import TextNode
from config.settings import settings
from utils.logger import get_logger

logger = get_logger("chunking_service")


class ChunkingService:
    """Service for text chunking using LlamaIndex."""

    def __init__(self):
        self.sentence_splitter: Optional[SentenceSplitter] = None
        self.is_initialized = False

    def initialize(self) -> None:
        """Initialize chunking service with LlamaIndex SentenceSplitter."""
        try:
            logger.info(
                "Initializing chunking service",
                extra={
                    "extra_fields": {
                        "chunk_size": settings.LLAMAINDEX_CHUNK_SIZE,
                        "chunk_overlap": settings.LLAMAINDEX_CHUNK_OVERLAP,
                    }
                },
            )

            # Initialize LlamaIndex SentenceSplitter
            self.sentence_splitter = SentenceSplitter(
                chunk_size=settings.LLAMAINDEX_CHUNK_SIZE,
                chunk_overlap=settings.LLAMAINDEX_CHUNK_OVERLAP,
                separator=" ",
                paragraph_separator="\n\n",
            )

            self.is_initialized = True
            logger.info("Chunking service initialized successfully")

        except Exception as e:
            logger.error(
                f"Failed to initialize chunking service: {str(e)}",
                extra={"extra_fields": {"error_type": type(e).__name__}},
            )
            self.is_initialized = False
            raise

    async def chunk_documents(
        self, documents: List[Document]
    ) -> List[TextNode]:
        """Chunk documents into smaller text nodes using LlamaIndex."""
        if not self.is_initialized or not self.sentence_splitter:
            raise RuntimeError("Chunking service not initialized")

        try:
            logger.info(
                "Chunking documents",
                extra={
                    "extra_fields": {
                        "document_count": len(documents),
                        "total_chars": sum(len(doc.text) for doc in documents),
                    }
                },
            )

            # Use LlamaIndex node parser to create chunks
            nodes = self.sentence_splitter.get_nodes_from_documents(documents)

            # Enrich nodes with additional metadata
            for i, node in enumerate(nodes):
                node.metadata.update(
                    {
                        "chunk_index": i,
                        "chunk_size": len(node.text),
                        "total_chunks": len(nodes),
                    }
                )

            logger.info(
                "Successfully chunked documents",
                extra={
                    "extra_fields": {
                        "document_count": len(documents),
                        "chunk_count": len(nodes),
                        "avg_chunk_size": (
                            sum(len(node.text) for node in nodes) / len(nodes)
                            if nodes
                            else 0
                        ),
                    }
                },
            )

            return nodes

        except Exception as e:
            logger.error(
                f"Failed to chunk documents: {str(e)}",
                extra={
                    "extra_fields": {
                        "error_type": type(e).__name__,
                        "document_count": len(documents),
                    }
                },
            )
            raise

    async def chunk_text(
        self, text: str, metadata: Optional[Dict[str, Any]] = None
    ) -> List[TextNode]:
        """Chunk raw text into nodes."""
        if not self.is_initialized or not self.sentence_splitter:
            raise RuntimeError("Chunking service not initialized")

        try:
            logger.debug(
                f"Chunking text",
                extra={"extra_fields": {"text_length": len(text)}},
            )

            # Create a document from text
            doc = Document(text=text, metadata=metadata or {})

            # Chunk the document
            nodes = await self.chunk_documents([doc])

            logger.debug(
                f"Successfully chunked text",
                extra={
                    "extra_fields": {
                        "text_length": len(text),
                        "chunk_count": len(nodes),
                    }
                },
            )

            return nodes

        except Exception as e:
            logger.error(
                f"Failed to chunk text: {str(e)}",
                extra={
                    "extra_fields": {
                        "error_type": type(e).__name__,
                        "text_length": len(text),
                    }
                },
            )
            raise

    def get_chunk_stats(self, nodes: List[TextNode]) -> Dict[str, Any]:
        """Get statistics about chunks."""
        try:
            if not nodes:
                return {
                    "chunk_count": 0,
                    "total_chars": 0,
                    "avg_chunk_size": 0,
                    "min_chunk_size": 0,
                    "max_chunk_size": 0,
                }

            chunk_sizes = [len(node.text) for node in nodes]

            return {
                "chunk_count": len(nodes),
                "total_chars": sum(chunk_sizes),
                "avg_chunk_size": sum(chunk_sizes) / len(chunk_sizes),
                "min_chunk_size": min(chunk_sizes),
                "max_chunk_size": max(chunk_sizes),
            }

        except Exception as e:
            logger.error(
                f"Failed to get chunk stats: {str(e)}",
                extra={"extra_fields": {"error_type": type(e).__name__}},
            )
            return {"error": str(e)}

    async def merge_small_chunks(
        self, nodes: List[TextNode], min_size: int = 100
    ) -> List[TextNode]:
        """Merge chunks that are too small."""
        try:
            logger.debug(
                f"Merging small chunks",
                extra={
                    "extra_fields": {
                        "node_count": len(nodes),
                        "min_size": min_size,
                    }
                },
            )

            merged_nodes = []
            current_node = None

            for node in nodes:
                if current_node is None:
                    current_node = node
                elif len(current_node.text) < min_size:
                    # Merge with current node
                    current_node.text = f"{current_node.text} {node.text}"
                    # Update metadata
                    current_node.metadata["chunk_size"] = len(current_node.text)
                else:
                    merged_nodes.append(current_node)
                    current_node = node

            # Add the last node
            if current_node is not None:
                merged_nodes.append(current_node)

            logger.debug(
                f"Successfully merged small chunks",
                extra={
                    "extra_fields": {
                        "original_count": len(nodes),
                        "merged_count": len(merged_nodes),
                    }
                },
            )

            return merged_nodes

        except Exception as e:
            logger.error(
                f"Failed to merge small chunks: {str(e)}",
                extra={"extra_fields": {"error_type": type(e).__name__}},
            )
            raise


# Global singleton instance
chunking_service = ChunkingService()
