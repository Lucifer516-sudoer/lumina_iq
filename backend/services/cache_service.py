"""
Redis Cache Service for Lumina IQ RAG Backend.

Provides multi-level caching with semantic cache support for embeddings,
retrieval results, and API responses.
"""

import hashlib
import json
from typing import Any, Optional, List, Dict
import redis.asyncio as redis
from redis.asyncio import Redis
from config.settings import settings
from utils.logger import get_logger

logger = get_logger("cache_service")


class CacheService:
    """Redis-based caching service with semantic cache support."""

    def __init__(self):
        self.redis_client: Optional[Redis] = None
        self.is_initialized = False

    async def initialize(self) -> None:
        """Initialize Redis connection."""
        try:
            # Parse Redis URL to extract components
            redis_url = settings.REDIS_URL
            if "://" not in redis_url:
                redis_url = f"redis://{redis_url}"

            logger.info(
                f"Initializing Redis cache service",
                extra={"extra_fields": {"redis_url": redis_url.split("@")[-1]}},
            )

            self.redis_client = await redis.from_url(
                redis_url,
                db=settings.REDIS_CACHE_DB,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=5,
                socket_keepalive=True,
                health_check_interval=30,
            )

            # Test connection
            await self.redis_client.ping()
            self.is_initialized = True

            logger.info("Redis cache service initialized successfully")

        except Exception as e:
            error_msg = str(e)
            logger.error(
                f"Failed to initialize Redis cache service: {error_msg}",
                extra={"extra_fields": {"error_type": type(e).__name__}},
            )
            
            # Provide helpful guidance for common errors
            if "Authentication" in error_msg or "NOAUTH" in error_msg:
                logger.warning(f"Redis authentication required. Update REDIS_URL in .env file with password: - format: {"redis://default:<password>@hostname:port"}, example: {"redis://default:mypassword@redis-host.com:13314"}, current_url: {redis_url.split("@")[-1]}")
            elif "Connection refused" in error_msg or "timeout" in error_msg.lower():
                logger.warning(f"Redis connection failed. Check if Redis server is running and accessible. - redis_url: {redis_url.split("@")[-1]}")
            
            self.is_initialized = False
            raise

    async def close(self) -> None:
        """Close Redis connection."""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Redis cache service closed")

    def _generate_key(self, prefix: str, *args: Any) -> str:
        """Generate cache key from prefix and arguments."""
        # Create a stable string representation of all arguments
        # Normalize strings to ensure consistent hashing
        key_parts = []
        for arg in args:
            if isinstance(arg, str):
                # Normalize whitespace: strip, convert multiple spaces to single space
                normalized = " ".join(arg.strip().split())
                key_parts.append(normalized)
            else:
                key_parts.append(str(arg))
        
        key_string = ":".join(key_parts)

        # Hash for consistent key length
        key_hash = hashlib.sha256(key_string.encode()).hexdigest()[:16]

        return f"{prefix}:{key_hash}"

    async def get(self, key: str) -> Optional[str]:
        """Get value from cache."""
        if not self.is_initialized or not self.redis_client:
            return None

        try:
            value = await self.redis_client.get(key)
            if value:
                logger.debug(f"Cache HIT: {key}")
            else:
                logger.debug(f"Cache MISS: {key}")
            return value
        except Exception as e:
            logger.error(
                f"Cache get error: {str(e)}",
                extra={"extra_fields": {"key": key, "error_type": type(e).__name__}},
            )
            return None

    async def set(
        self, key: str, value: str, ttl: Optional[int] = None
    ) -> bool:
        """Set value in cache with optional TTL."""
        if not self.is_initialized or not self.redis_client:
            return False

        try:
            ttl = ttl or settings.CACHE_TTL_SECONDS
            await self.redis_client.setex(key, ttl, value)
            logger.debug(
                f"Cache SET: {key}",
                extra={"extra_fields": {"ttl": ttl}},
            )
            return True
        except Exception as e:
            logger.error(
                f"Cache set error: {str(e)}",
                extra={"extra_fields": {"key": key, "error_type": type(e).__name__}},
            )
            return False

    async def delete(self, key: str) -> bool:
        """Delete value from cache."""
        if not self.is_initialized or not self.redis_client:
            return False

        try:
            await self.redis_client.delete(key)
            logger.debug(f"Cache DELETE: {key}")
            return True
        except Exception as e:
            logger.error(
                f"Cache delete error: {str(e)}",
                extra={"extra_fields": {"key": key, "error_type": type(e).__name__}},
            )
            return False

    async def get_json(self, key: str) -> Optional[Any]:
        """Get JSON value from cache."""
        value = await self.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError as e:
                logger.error(
                    f"Failed to decode JSON from cache: {str(e)}",
                    extra={"extra_fields": {"key": key}},
                )
        return None

    async def set_json(
        self, key: str, value: Any, ttl: Optional[int] = None
    ) -> bool:
        """Set JSON value in cache."""
        try:
            json_value = json.dumps(value)
            return await self.set(key, json_value, ttl)
        except (TypeError, ValueError) as e:
            logger.error(
                f"Failed to encode JSON for cache: {str(e)}",
                extra={"extra_fields": {"key": key}},
            )
            return False

    async def cache_embedding(
        self, text: str, embedding: List[float], model: str
    ) -> bool:
        """Cache embedding for text."""
        key = self._generate_key("embed", model, text)
        return await self.set_json(key, embedding, ttl=86400)  # 24 hours

    async def get_cached_embedding(
        self, text: str, model: str
    ) -> Optional[List[float]]:
        """Get cached embedding for text."""
        key = self._generate_key("embed", model, text)
        return await self.get_json(key)

    async def cache_retrieval_results(
        self, query: str, results: List[Dict[str, Any]], context: Dict[str, Any]
    ) -> bool:
        """Cache retrieval results for a query."""
        key = self._generate_key("retrieval", json.dumps(context, sort_keys=True), query)
        return await self.set_json(
            key, {"query": query, "results": results, "context": context}, ttl=3600
        )  # 1 hour

    async def get_cached_retrieval_results(
        self, query: str, context: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Get cached retrieval results for a query."""
        key = self._generate_key("retrieval", json.dumps(context, sort_keys=True), query)
        return await self.get_json(key)

    async def cache_api_response(
        self, endpoint: str, params: Dict[str, Any], response: Any
    ) -> bool:
        """Cache API response."""
        key = self._generate_key("api", endpoint, json.dumps(params, sort_keys=True))
        return await self.set_json(key, response, ttl=1800)  # 30 minutes

    async def get_cached_api_response(
        self, endpoint: str, params: Dict[str, Any]
    ) -> Optional[Any]:
        """Get cached API response."""
        key = self._generate_key("api", endpoint, json.dumps(params, sort_keys=True))
        return await self.get_json(key)

    async def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate all keys matching pattern."""
        if not self.is_initialized or not self.redis_client:
            return 0

        try:
            keys = []
            async for key in self.redis_client.scan_iter(match=pattern):
                keys.append(key)

            if keys:
                deleted = await self.redis_client.delete(*keys)
                logger.info(
                    f"Invalidated {deleted} cache keys",
                    extra={"extra_fields": {"pattern": pattern}},
                )
                return deleted
            return 0
        except Exception as e:
            logger.error(
                f"Cache invalidation error: {str(e)}",
                extra={"extra_fields": {"pattern": pattern, "error_type": type(e).__name__}},
            )
            return 0

    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        if not self.is_initialized or not self.redis_client:
            return {"status": "disconnected"}

        try:
            info = await self.redis_client.info()
            return {
                "status": "connected",
                "used_memory": info.get("used_memory_human"),
                "connected_clients": info.get("connected_clients"),
                "total_commands": info.get("total_commands_processed"),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "hit_rate": (
                    info.get("keyspace_hits", 0)
                    / (info.get("keyspace_hits", 0) + info.get("keyspace_misses", 1))
                    * 100
                ),
            }
        except Exception as e:
            logger.error(
                f"Failed to get cache stats: {str(e)}",
                extra={"extra_fields": {"error_type": type(e).__name__}},
            )
            return {"status": "error", "error": str(e)}


# Global singleton instance
cache_service = CacheService()
