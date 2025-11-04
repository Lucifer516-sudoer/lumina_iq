"""
Embedding Service for Lumina IQ RAG Backend.

Handles embedding generation using direct API calls to Together AI.
"""

from typing import List, Dict, Any, Optional
import httpx
from config.settings import settings
from utils.logger import get_logger
from .cache_service import cache_service

logger = get_logger("embedding_service")


class EmbeddingService:
    """Service for generating embeddings using direct Together AI API calls."""

    def __init__(self):
        self.api_key: Optional[str] = None
        self.base_url: str = ""
        self.model: str = ""
        self.client: Optional[httpx.AsyncClient] = None
        self.is_initialized = False

    def initialize(self) -> None:
        """Initialize Together AI embedding service with direct API access."""
        try:
            if not settings.TOGETHER_API_KEY:
                logger.warning("TOGETHER_API_KEY not configured")
                return

            logger.info(f"Initializing embedding service - model: {settings.EMBEDDING_MODEL}, provider: Together AI (Direct API)")

            self.api_key = settings.TOGETHER_API_KEY
            self.base_url = settings.TOGETHER_BASE_URL.rstrip("/")
            self.model = settings.EMBEDDING_MODEL
            
            # Initialize HTTP client
            self.client = httpx.AsyncClient(
                timeout=60.0,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                }
            )

            self.is_initialized = True
            logger.info("Embedding service initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize embedding service: {str(e)} - error_type: {type(e).__name__}")
            self.is_initialized = False
            raise
    
    async def cleanup(self) -> None:
        """Cleanup resources."""
        if self.client:
            await self.client.aclose()
            self.client = None
        self.is_initialized = False
    
    async def _call_embedding_api(self, texts: List[str]) -> List[List[float]]:
        """Make direct API call to Together AI embeddings endpoint."""
        if not self.client:
            raise RuntimeError("HTTP client not initialized")
        
        try:
            # Together AI embeddings endpoint expects this format
            payload = {
                "model": self.model,
                "input": texts
            }
            
            response = await self.client.post(
                f"{self.base_url}/embeddings",
                json=payload
            )
            
            if response.status_code != 200:
                error_detail = response.text
                logger.error(f"Embedding API error: {response.status_code} - response: {error_detail}, texts_count: {len(texts)}")
                raise RuntimeError(f"Error code: {response.status_code} - {error_detail}")
            
            data = response.json()
            
            # Extract embeddings from response
            # Together AI returns: {"object": "list", "data": [{"embedding": [...], "index": 0}, ...]}
            if "data" not in data:
                raise RuntimeError(f"Unexpected API response format: {data}")
            
            # Sort by index to maintain order
            sorted_data = sorted(data["data"], key=lambda x: x.get("index", 0))
            embeddings = [item["embedding"] for item in sorted_data]
            
            return embeddings
            
        except httpx.HTTPError as e:
            logger.error(f"HTTP error calling embedding API: {str(e)} - error_type: {type(e).__name__}")
            raise
        except Exception as e:
            logger.error(f"Error calling embedding API: {str(e)} - error_type: {type(e).__name__}")
            raise

    async def generate_embedding(
        self, text: str, use_cache: bool = True
    ) -> List[float]:
        """Generate embedding for text with optional caching."""
        if not self.is_initialized or not self.client:
            raise RuntimeError("Embedding service not initialized")

        try:
            # Sanitize input text
            if not text or not isinstance(text, str):
                text = " "
            else:
                text = text.strip()
                if not text:
                    text = " "
                # Limit text length to 120k chars (for 32k token model)
                if len(text) > 120000:
                    text = text[:120000]

            # Check cache first if enabled
            if use_cache and settings.CACHE_EMBEDDINGS:
                cached_embedding = await cache_service.get_cached_embedding(
                    text, settings.EMBEDDING_MODEL
                )
                if cached_embedding:
                    logger.debug(f"Using cached embedding - text_length: {len(text)}")
                    return cached_embedding

            logger.debug(f"Generating embedding for text - text_length: {len(text)}, model: {settings.EMBEDDING_MODEL}")

            # Generate embedding using direct API call
            embeddings = await self._call_embedding_api([text])
            embedding = embeddings[0]

            # Cache the embedding if enabled
            if use_cache and settings.CACHE_EMBEDDINGS:
                await cache_service.cache_embedding(
                    text, embedding, settings.EMBEDDING_MODEL
                )

            logger.debug(f"Generated embedding successfully - embedding_dim: {len(embedding)}, text_length: {len(text)}")

            return embedding

        except Exception as e:
            logger.error(f"Failed to generate embedding: {str(e)} - error_type: {type(e).__name__}, text_length: {len(text)}")
            raise

    async def generate_embeddings_batch(
        self, texts: List[str], use_cache: bool = True
    ) -> List[List[float]]:
        """Generate embeddings for multiple texts with batching and caching."""
        if not self.is_initialized or not self.client:
            raise RuntimeError("Embedding service not initialized")

        try:
            logger.info(f"Generating embeddings for batch - batch_size: {len(texts)}, model: {settings.EMBEDDING_MODEL}")

            embeddings = []
            texts_to_embed = []
            cache_indices = []

            # Check cache for each text if enabled
            if use_cache and settings.CACHE_EMBEDDINGS:
                for i, text in enumerate(texts):
                    cached_embedding = await cache_service.get_cached_embedding(
                        text, settings.EMBEDDING_MODEL
                    )
                    if cached_embedding:
                        embeddings.append((i, cached_embedding))
                    else:
                        texts_to_embed.append(text)
                        cache_indices.append(i)

                logger.debug(f"Cache stats for batch - cached: {len(embeddings)}, to_generate: {len(texts_to_embed)}")
            else:
                texts_to_embed = texts
                cache_indices = list(range(len(texts)))

            # Generate embeddings for uncached texts
            if texts_to_embed:
                # Validate and sanitize texts before embedding
                sanitized_texts = []
                for text in texts_to_embed:
                    # Ensure text is not empty and is a string
                    if not text or not isinstance(text, str):
                        sanitized_texts.append(" ")  # Use single space for empty/invalid texts
                    else:
                        # Trim whitespace and ensure non-empty
                        sanitized = text.strip()
                        if not sanitized:
                            sanitized = " "
                        # Limit text length to avoid token limits (32k tokens ≈ 128k chars)
                        # Using 120k chars to be safe and leave room for special tokens
                        if len(sanitized) > 120000:
                            sanitized = sanitized[:120000]
                        sanitized_texts.append(sanitized)
                
                # Process in batches to avoid rate limits
                batch_size = settings.EMBEDDING_BATCH_SIZE
                new_embeddings = []

                for i in range(0, len(sanitized_texts), batch_size):
                    batch = sanitized_texts[i : i + batch_size]
                    batch_embeddings = await self._call_embedding_api(batch)
                    new_embeddings.extend(batch_embeddings)

                    logger.debug(f"Generated batch embeddings - batch_start: {i}, batch_size: {len(batch)}")

                # Cache new embeddings if enabled
                if use_cache and settings.CACHE_EMBEDDINGS:
                    for text, embedding in zip(texts_to_embed, new_embeddings):
                        await cache_service.cache_embedding(
                            text, embedding, settings.EMBEDDING_MODEL
                        )

                # Merge with cached embeddings
                for idx, embedding in zip(cache_indices, new_embeddings):
                    embeddings.append((idx, embedding))

            # Sort by original index to maintain order
            embeddings.sort(key=lambda x: x[0])
            result_embeddings = [emb for _, emb in embeddings]

            embedding_dim = len(result_embeddings[0]) if result_embeddings else 0
            logger.info(f"Generated batch embeddings successfully - total_embeddings: {len(result_embeddings)}, embedding_dim: {embedding_dim}")

            return result_embeddings

        except Exception as e:
            logger.error(f"Failed to generate batch embeddings: {str(e)} - error_type: {type(e).__name__}, batch_size: {len(texts)}")
            raise

    async def compute_similarity(
        self, embedding1: List[float], embedding2: List[float]
    ) -> float:
        """Compute cosine similarity between two embeddings."""
        try:
            import math

            # Compute dot product
            dot_product = sum(a * b for a, b in zip(embedding1, embedding2))

            # Compute magnitudes
            magnitude1 = math.sqrt(sum(a * a for a in embedding1))
            magnitude2 = math.sqrt(sum(b * b for b in embedding2))

            # Compute cosine similarity
            similarity = dot_product / (magnitude1 * magnitude2)

            return similarity

        except Exception as e:
            logger.error(f"Failed to compute similarity: {str(e)} - error_type: {type(e).__name__}")
            raise

    async def find_similar_texts(
        self, query_embedding: List[float], candidate_embeddings: List[List[float]]
    ) -> List[Dict[str, Any]]:
        """Find most similar texts to query embedding."""
        try:
            similarities = []

            for i, candidate_embedding in enumerate(candidate_embeddings):
                similarity = await self.compute_similarity(
                    query_embedding, candidate_embedding
                )
                similarities.append({"index": i, "similarity": similarity})

            # Sort by similarity descending
            similarities.sort(key=lambda x: x["similarity"], reverse=True)

            return similarities

        except Exception as e:
            logger.error(f"Failed to find similar texts: {str(e)} - error_type: {type(e).__name__}")
            raise


# Global singleton instance
embedding_service = EmbeddingService()
