"""
Qdrant Vector Database Service for Lumina IQ RAG Backend.

Provides vector storage and retrieval operations using Qdrant Cloud.
"""

from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
    SearchRequest,
)
from config.settings import settings
from utils.logger import get_logger
import uuid

logger = get_logger("qdrant_service")


class QdrantService:
    """Service for interacting with Qdrant vector database."""

    def __init__(self):
        self.client: Optional[QdrantClient] = None
        self.collection_name: str = settings.QDRANT_COLLECTION_NAME
        self.is_initialized = False

    def initialize(self) -> None:
        """Initialize Qdrant client and ensure collection exists."""
        try:
            logger.info(
                "Initializing Qdrant service",
                extra={
                    "extra_fields": {
                        "collection": self.collection_name,
                        "url": settings.QDRANT_URL,
                    }
                },
            )

            self.client = QdrantClient(
                url=settings.QDRANT_URL,
                api_key=settings.QDRANT_API_KEY,
                timeout=30,
                # Disable compatibility check - client 1.13.3 works with server 1.15.5
                check_compatibility=False,
                prefer_grpc=False,
            )

            # Check if collection exists, create if not
            collections = self.client.get_collections().collections
            collection_names = [col.name for col in collections]

            if self.collection_name not in collection_names:
                logger.info(
                    f"Creating collection: {self.collection_name}",
                    extra={
                        "extra_fields": {
                            "dimensions": settings.EMBEDDING_DIMENSIONS,
                            "distance": "Cosine",
                        }
                    },
                )

                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=settings.EMBEDDING_DIMENSIONS,
                        distance=Distance.COSINE,
                    ),
                )

                logger.info(f"Collection created: {self.collection_name}")
            else:
                logger.info(f"Collection already exists: {self.collection_name}")

            # Create payload index for file_hash field to enable filtering
            try:
                self.client.create_payload_index(
                    collection_name=self.collection_name,
                    field_name="file_hash",
                    field_schema="keyword"
                )
                logger.info(f"Created payload index for file_hash field")
            except Exception as index_error:
                # Index might already exist, which is fine
                logger.debug(f"Payload index for file_hash may already exist: {str(index_error)}")

            self.is_initialized = True
            logger.info("Qdrant service initialized successfully")

        except Exception as e:
            logger.error(
                f"Failed to initialize Qdrant service: {str(e)}",
                extra={"extra_fields": {"error_type": type(e).__name__}},
            )
            self.is_initialized = False
            raise

    async def upsert_points(
        self,
        texts: List[str],
        embeddings: List[List[float]],
        metadata: List[Dict[str, Any]],
    ) -> List[str]:
        """Insert or update points in Qdrant collection."""
        if not self.is_initialized or not self.client:
            raise RuntimeError("Qdrant service not initialized")

        try:
            if len(texts) != len(embeddings) or len(texts) != len(metadata):
                raise ValueError("Texts, embeddings, and metadata must have same length")

            logger.info(
                "Upserting points to Qdrant",
                extra={
                    "extra_fields": {
                        "count": len(texts),
                        "collection": self.collection_name,
                    }
                },
            )

            points = []
            point_ids = []

            for text, embedding, meta in zip(texts, embeddings, metadata):
                point_id = str(uuid.uuid4())
                point_ids.append(point_id)

                # Add text to metadata
                payload = {**meta, "text": text}

                point = PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload=payload,
                )
                points.append(point)

            # Upsert in batches
            batch_size = 100
            for i in range(0, len(points), batch_size):
                batch = points[i : i + batch_size]
                self.client.upsert(
                    collection_name=self.collection_name,
                    points=batch,
                )

            logger.info(
                f"Successfully upserted {len(points)} points",
                extra={
                    "extra_fields": {
                        "collection": self.collection_name,
                        "point_ids": point_ids[:5],  # Log first 5 IDs
                    }
                },
            )

            return point_ids

        except Exception as e:
            logger.error(
                f"Failed to upsert points: {str(e)}",
                extra={
                    "extra_fields": {
                        "error_type": type(e).__name__,
                        "count": len(texts),
                    }
                },
            )
            raise

    async def search(
        self,
        query_vector: List[float],
        limit: int = 10,
        filter_conditions: Optional[Dict[str, Any]] = None,
        score_threshold: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """Search for similar vectors in Qdrant collection."""
        if not self.is_initialized or not self.client:
            raise RuntimeError("Qdrant service not initialized")

        try:
            logger.debug(
                "Searching Qdrant",
                extra={
                    "extra_fields": {
                        "limit": limit,
                        "has_filter": bool(filter_conditions),
                        "score_threshold": score_threshold,
                    }
                },
            )

            # Build filter if conditions provided
            search_filter = None
            if filter_conditions:
                conditions = []
                for key, value in filter_conditions.items():
                    conditions.append(
                        FieldCondition(
                            key=key,
                            match=MatchValue(value=value),
                        )
                    )
                search_filter = Filter(must=conditions)

            # Perform search
            search_result = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=limit,
                query_filter=search_filter,
                score_threshold=score_threshold,
            )

            # Format results
            results = []
            for point in search_result:
                result = {
                    "id": point.id,
                    "score": point.score,
                    "text": point.payload.get("text", ""),
                    "metadata": {
                        k: v for k, v in point.payload.items() if k != "text"
                    },
                }
                results.append(result)

            logger.debug(
                f"Found {len(results)} results",
                extra={
                    "extra_fields": {
                        "result_count": len(results),
                        "top_score": results[0]["score"] if results else None,
                    }
                },
            )

            return results

        except Exception as e:
            logger.error(
                f"Failed to search Qdrant: {str(e)}",
                extra={
                    "extra_fields": {
                        "error_type": type(e).__name__,
                        "limit": limit,
                    }
                },
            )
            raise

    async def delete_points(
        self, filter_conditions: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Delete points matching filter conditions."""
        if not self.is_initialized or not self.client:
            raise RuntimeError("Qdrant service not initialized")

        try:
            logger.info(
                "Deleting points from Qdrant",
                extra={"extra_fields": {"filter": filter_conditions}},
            )

            # Build filter
            conditions = []
            for key, value in filter_conditions.items():
                conditions.append(
                    FieldCondition(
                        key=key,
                        match=MatchValue(value=value),
                    )
                )
            delete_filter = Filter(must=conditions)

            # Delete points
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=delete_filter,
            )

            logger.info(
                "Successfully deleted points",
                extra={"extra_fields": {"filter": filter_conditions}},
            )

            return {"status": "success", "filter": filter_conditions}

        except Exception as e:
            logger.error(
                f"Failed to delete points: {str(e)}",
                extra={
                    "extra_fields": {
                        "error_type": type(e).__name__,
                        "filter": filter_conditions,
                    }
                },
            )
            raise

    async def get_collection_info(self) -> Dict[str, Any]:
        """Get collection information and statistics."""
        if not self.is_initialized or not self.client:
            raise RuntimeError("Qdrant service not initialized")

        try:
            collection_info = self.client.get_collection(
                collection_name=self.collection_name
            )

            return {
                "name": self.collection_name,
                "points_count": collection_info.points_count,
                "vectors_count": collection_info.vectors_count,
                "status": collection_info.status,
                "config": {
                    "distance": str(collection_info.config.params.vectors.distance),
                    "size": collection_info.config.params.vectors.size,
                },
            }

        except Exception as e:
            logger.error(
                f"Failed to get collection info: {str(e)}",
                extra={"extra_fields": {"error_type": type(e).__name__}},
            )
            raise

    def scroll_points(
        self,
        filter_conditions: Optional[Dict[str, Any]] = None,
        limit: int = 100,
        offset: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Scroll through points in collection."""
        if not self.is_initialized or not self.client:
            raise RuntimeError("Qdrant service not initialized")

        try:
            # Build filter if conditions provided
            scroll_filter = None
            if filter_conditions:
                conditions = []
                for key, value in filter_conditions.items():
                    conditions.append(
                        FieldCondition(
                            key=key,
                            match=MatchValue(value=value),
                        )
                    )
                scroll_filter = Filter(must=conditions)

            # Scroll points
            result = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=scroll_filter,
                limit=limit,
                offset=offset,
            )

            points = [
                {
                    "id": point.id,
                    "payload": point.payload,
                }
                for point in result[0]
            ]

            return {
                "points": points,
                "next_offset": result[1],
            }

        except Exception as e:
            logger.error(
                f"Failed to scroll points: {str(e)}",
                extra={"extra_fields": {"error_type": type(e).__name__}},
            )
            raise

    def check_document_exists(self, file_hash: str) -> bool:
        """Check if a document with the given file_hash already exists in the collection."""
        if not self.is_initialized or not self.client:
            raise RuntimeError("Qdrant service not initialized")

        try:
            # Scroll with file_hash filter to check if any points exist
            result = self.scroll_points(
                filter_conditions={"file_hash": file_hash},
                limit=1
            )
            
            exists = len(result.get("points", [])) > 0
            
            if exists:
                logger.info(f"Document already exists in collection - file_hash: {file_hash[:8]}")
            
            return exists

        except Exception as e:
            logger.error(
                f"Failed to check document existence: {str(e)}",
                extra={"extra_fields": {"error_type": type(e).__name__, "file_hash": file_hash[:8]}},
            )
            # On error, return False to allow ingestion attempt
            return False


# Global singleton instance
qdrant_service = QdrantService()
