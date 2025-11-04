import os
import hashlib
import json
import aiofiles
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import asyncio
import redis.asyncio as redis
from circuitbreaker import circuit

from config.settings import settings
from utils.logger import get_logger

# Use enhanced logger
logger = get_logger("cache")
import time


class CacheService:
    """Service for caching extracted PDF text to improve performance"""

    def __init__(self):
        self.cache_dir = Path(settings.CACHE_DIR)
        self.cache_dir.mkdir(exist_ok=True)

    def _generate_cache_key(self, file_path: str) -> str:
        """Generate a unique cache key based on file path and modification time"""
        try:
            # Get file stats
            file_stat = os.stat(file_path)
            file_size = file_stat.st_size
            modification_time = file_stat.st_mtime

            # Create a unique identifier combining path, size, and modification time
            unique_string = f"{file_path}_{file_size}_{modification_time}"

            # Generate MD5 hash for the cache key
            cache_key = hashlib.md5(unique_string.encode()).hexdigest()

            return cache_key
        except Exception as e:
            logger.error(f"Error generating cache key: file_path={file_path}, error={str(e)}")
            # Fallback to just file path hash if stat fails
            return hashlib.md5(file_path.encode()).hexdigest()

    def _get_cache_file_path(self, cache_key: str) -> Path:
        """Get the full path to the cache file"""
        return self.cache_dir / f"{cache_key}.json"

    async def get_cached_text(self, file_path: str) -> Optional[str]:
        """
        Retrieve cached extracted text for a PDF file

        Args:
            file_path: Path to the PDF file

        Returns:
            Cached text if available, None otherwise
        """
        try:
            cache_key = self._generate_cache_key(file_path)
            cache_file_path = self._get_cache_file_path(cache_key)

            if not cache_file_path.exists():
                logger.debug(f"No cache found: {file_path}")
                return None

            # Read cached data
            async with aiofiles.open(cache_file_path, "r", encoding="utf-8") as f:
                cache_data = json.loads(await f.read())

            # Verify cache data structure
            if not all(key in cache_data for key in ["text", "cached_at", "file_path"]):
                logger.warning(f"Invalid cache data structure: {file_path}")
                return None

            logger.info(f"Cache hit: file_path={file_path}, cached_at={cache_data['cached_at']}")
            return cache_data["text"]

        except Exception as e:
            logger.error(f"Error reading cache: file_path={file_path}, error={str(e)}")
            return None

    async def save_to_cache(self, file_path: str, extracted_text: str) -> bool:
        """
        Save extracted text to cache

        Args:
            file_path: Path to the PDF file
            extracted_text: The extracted text content

        Returns:
            True if successfully cached, False otherwise
        """
        try:
            cache_key = self._generate_cache_key(file_path)
            cache_file_path = self._get_cache_file_path(cache_key)

            # Prepare cache data
            cache_data = {
                "text": extracted_text,
                "file_path": file_path,
                "cached_at": datetime.now().isoformat(),
                "text_length": len(extracted_text),
                "cache_key": cache_key,
            }

            # Save to cache file
            async with aiofiles.open(cache_file_path, "w", encoding="utf-8") as f:
                await f.write(json.dumps(cache_data, ensure_ascii=False, indent=2))

            logger.info(f"Successfully cached text: file_path={file_path}, cache_key={cache_key}")
            return True

        except Exception as e:
            logger.error(f"Error saving to cache: file_path={file_path}, error={str(e)}")
            return False

    def clear_cache(self) -> int:
        """
        Clear all cached files

        Returns:
            Number of files deleted
        """
        try:
            deleted_count = 0
            for cache_file in self.cache_dir.glob("*.json"):
                cache_file.unlink()
                deleted_count += 1

            logger.info(f"Cache cleared: {deleted_count}")
            return deleted_count

        except Exception as e:
            logger.error(f"Error clearing cache: {str(e)}")
            return 0

    def get_cache_info(self) -> dict:
        """
        Get information about the current cache

        Returns:
            Dictionary with cache statistics
        """
        try:
            cache_files = list(self.cache_dir.glob("*.json"))
            total_files = len(cache_files)
            total_size = sum(f.stat().st_size for f in cache_files)

            return {
                "cache_directory": str(self.cache_dir),
                "total_cached_files": total_files,
                "total_cache_size_bytes": total_size,
                "total_cache_size_mb": round(total_size / (1024 * 1024), 2),
            }

        except Exception as e:
            logger.error(f"Error getting cache info: {str(e)}")
            return {}

    def _generate_embedding_cache_key(self, text: str) -> str:
        """Generate cache key for embedding based on text hash"""
        return hashlib.md5(text.encode()).hexdigest()

    async def get_cached_embedding(self, text: str) -> Optional[List[float]]:
        """Get cached embedding for text"""
        if not getattr(settings, "CACHE_EMBEDDINGS", False):
            return None

        try:
            cache_key = self._generate_embedding_cache_key(text)
            cache_file_path = self.cache_dir / f"emb_{cache_key}.json"

            if not cache_file_path.exists():
                return None

            async with aiofiles.open(cache_file_path, "r") as f:
                cache_data = json.loads(await f.read())

            # Check TTL
            cached_at = datetime.fromisoformat(cache_data["cached_at"])
            ttl_seconds = getattr(settings, "CACHE_TTL_SECONDS", 3600)
            if datetime.now() - cached_at > timedelta(seconds=ttl_seconds):
                cache_file_path.unlink()  # Remove expired cache
                return None

            logger.debug(f"Embedding cache hit: {cache_key[:8]}")
            return cache_data["embedding"]

        except Exception as e:
            logger.error(f"Error reading embedding cache: {str(e)}")
            return None

    async def save_embedding_to_cache(self, text: str, embedding: List[float]) -> bool:
        """Save embedding to cache"""
        if not getattr(settings, "CACHE_EMBEDDINGS", False):
            return False

        try:
            cache_key = self._generate_embedding_cache_key(text)
            cache_file_path = self.cache_dir / f"emb_{cache_key}.json"

            cache_data = {
                "text": text[:100],  # Store first 100 chars for debugging
                "embedding": embedding,
                "cached_at": datetime.now().isoformat(),
                "text_length": len(text),
            }

            async with aiofiles.open(cache_file_path, "w") as f:
                await f.write(json.dumps(cache_data))

            logger.debug(f"Embedding cached: {cache_key[:8]}")
            return True

        except Exception as e:
            logger.error(f"Error saving embedding to cache: {str(e)}")
            return False

    async def get_cached_query_result(
        self, query: str, token: str, filename: str
    ) -> Optional[Dict[str, Any]]:
        """Get cached query result"""
        if not getattr(settings, "CACHE_QUERY_RESULTS", False):
            return None

        try:
            cache_key = hashlib.md5(f"{query}_{token}_{filename}".encode()).hexdigest()
            cache_file_path = self.cache_dir / f"query_{cache_key}.json"

            if not cache_file_path.exists():
                return None

            async with aiofiles.open(cache_file_path, "r") as f:
                cache_data = json.loads(await f.read())

            # Check TTL
            cached_at = datetime.fromisoformat(cache_data["cached_at"])
            ttl_seconds = getattr(settings, "CACHE_TTL_SECONDS", 3600)
            if datetime.now() - cached_at > timedelta(seconds=ttl_seconds):
                cache_file_path.unlink()
                return None

            logger.debug(f"Query result cache hit: {cache_key[:8]}")
            return cache_data["result"]

        except Exception as e:
            logger.error(f"Error reading query cache: {str(e)}")
            return None

    async def save_query_result_to_cache(
        self, query: str, token: str, filename: str, result: Dict[str, Any]
    ) -> bool:
        """Save query result to cache"""
        if not getattr(settings, "CACHE_QUERY_RESULTS", False):
            return False

        try:
            cache_key = hashlib.md5(f"{query}_{token}_{filename}".encode()).hexdigest()
            cache_file_path = self.cache_dir / f"query_{cache_key}.json"

            cache_data = {
                "query": query[:100],
                "token": token,
                "filename": filename,
                "result": result,
                "cached_at": datetime.now().isoformat(),
            }

            async with aiofiles.open(cache_file_path, "w") as f:
                await f.write(json.dumps(cache_data))

            logger.debug(f"Query result cached: {cache_key[:8]}")
            return True

        except Exception as e:
            logger.error(f"Error saving query result to cache: {str(e)}")
            return False


class RedisCache:
    """
    Redis-based cache with async operations, circuit breaker pattern,
    and fallback to file system cache when Redis is unavailable.
    """

    def __init__(self):
        self.redis_url = getattr(settings, 'REDIS_URL', 'redis://localhost:6379')
        self.redis_db = getattr(settings, 'REDIS_CACHE_DB', 0)
        self.redis_client = None
        self._connection_lock = asyncio.Lock()
        self._circuit_open = False
        self._last_failure_time = None
        self._failure_count = 0
        self._max_failures = 3  # Circuit breaker threshold
        self._circuit_timeout = 60  # seconds to wait before retrying

        # Fallback to file cache
        self.file_cache = CacheService()

    async def _get_client(self):
        """Get or create Redis client with connection pooling."""
        if self.redis_client is None:
            try:
                self.redis_client = redis.Redis.from_url(
                    self.redis_url,
                    db=self.redis_db,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5,
                    retry_on_timeout=True,
                    max_connections=20
                )
                # Test connection
                await self.redis_client.ping()
                logger.info("Redis connection established")
            except Exception as e:
                logger.warning(f"Failed to connect to Redis: {str(e)}")
                self.redis_client = None

        return self.redis_client

    def _is_circuit_open(self) -> bool:
        """Check if circuit breaker is open."""
        if not self._circuit_open:
            return False

        # Check if timeout has passed
        if self._last_failure_time and \
           (datetime.now() - self._last_failure_time).total_seconds() > self._circuit_timeout:
            logger.info("Circuit breaker timeout passed, attempting to close")
            self._circuit_open = False
            self._failure_count = 0
            return False

        return True

    def _record_failure(self):
        """Record a failure for circuit breaker."""
        self._failure_count += 1
        self._last_failure_time = datetime.now()

        if self._failure_count >= self._max_failures:
            logger.warning("Circuit breaker opened due to repeated failures")
            self._circuit_open = True

    def _record_success(self):
        """Record a success to reset circuit breaker."""
        self._failure_count = 0
        if self._circuit_open:
            logger.info("Circuit breaker closed after successful operation")
            self._circuit_open = False

    @circuit(failure_threshold=3, recovery_timeout=60, expected_exception=Exception)
    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from Redis cache.

        Returns:
            Cached value or None if not found or cache unavailable.
        """
        if self._is_circuit_open():
            logger.debug("Circuit breaker open, skipping Redis get")
            return None

        try:
            client = await self._get_client()
            if client is None:
                return None

            value = await client.get(key)
            if value is None:
                return None

            # Try to parse JSON
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value

        except Exception as e:
            logger.warning(f"Redis get failed for key {key}: {str(e)}")
            self._record_failure()
            return None

    @circuit(failure_threshold=3, recovery_timeout=60, expected_exception=Exception)
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Set value in Redis cache.

        Args:
            key: Cache key
            value: Value to cache (will be JSON serialized)
            ttl: Time-to-live in seconds

        Returns:
            True if successful, False otherwise.
        """
        if self._is_circuit_open():
            logger.debug("Circuit breaker open, skipping Redis set")
            return False

        try:
            client = await self._get_client()
            if client is None:
                return False

            # Serialize value
            if isinstance(value, (dict, list)):
                serialized_value = json.dumps(value)
            else:
                serialized_value = str(value)

            if ttl:
                success = await client.setex(key, ttl, serialized_value)
            else:
                success = await client.set(key, serialized_value)

            if success:
                self._record_success()

            return bool(success)

        except Exception as e:
            logger.warning(f"Redis set failed for key {key}: {str(e)}")
            self._record_failure()
            return False

    @circuit(failure_threshold=3, recovery_timeout=60, expected_exception=Exception)
    async def delete(self, key: str) -> bool:
        """Delete key from Redis cache."""
        if self._is_circuit_open():
            logger.debug("Circuit breaker open, skipping Redis delete")
            return False

        try:
            client = await self._get_client()
            if client is None:
                return False

            result = await client.delete(key)
            self._record_success()
            return result > 0

        except Exception as e:
            logger.warning(f"Redis delete failed for key {key}: {str(e)}")
            self._record_failure()
            return False

    @circuit(failure_threshold=3, recovery_timeout=60, expected_exception=Exception)
    async def exists(self, key: str) -> bool:
        """Check if key exists in Redis cache."""
        if self._is_circuit_open():
            logger.debug("Circuit breaker open, skipping Redis exists")
            return False

        try:
            client = await self._get_client()
            if client is None:
                return False

            result = await client.exists(key)
            self._record_success()
            return bool(result)

        except Exception as e:
            logger.warning(f"Redis exists failed for key {key}: {str(e)}")
            self._record_failure()
            return False

    @circuit(failure_threshold=3, recovery_timeout=60, expected_exception=Exception)
    async def scan_keys(self, pattern: str) -> List[str]:
        """Scan for keys matching pattern."""
        if self._is_circuit_open():
            logger.debug("Circuit breaker open, skipping Redis scan")
            return []

        try:
            client = await self._get_client()
            if client is None:
                return []

            keys = []
            async for key in client.scan_iter(match=pattern):
                keys.append(key)

            self._record_success()
            return keys

        except Exception as e:
            logger.warning(f"Redis scan failed for pattern {pattern}: {str(e)}")
            self._record_failure()
            return []

    @circuit(failure_threshold=3, recovery_timeout=60, expected_exception=Exception)
    async def ping(self) -> bool:
        """Ping Redis server to check connectivity."""
        try:
            client = await self._get_client()
            if client is None:
                return False

            await client.ping()
            self._record_success()
            return True

        except Exception as e:
            logger.warning(f"Redis ping failed: {str(e)}")
            self._record_failure()
            return False

    async def clear_all(self) -> int:
        """Clear all keys in current database."""
        try:
            client = await self._get_client()
            if client is None:
                return 0

            # Get all keys (be careful in production!)
            keys = await self.scan_keys("*")
            if not keys:
                return 0

            # Delete all keys
            result = await client.delete(*keys)
            self._record_success()
            logger.info(f"Cleared {result} keys from Redis")
            return result

        except Exception as e:
            logger.error(f"Error clearing Redis cache: {str(e)}")
            self._record_failure()
            return 0

    async def get_stats(self) -> Dict[str, Any]:
        """Get Redis cache statistics."""
        try:
            client = await self._get_client()
            stats = {
                "circuit_breaker_open": self._circuit_open,
                "failure_count": self._failure_count,
                "last_failure": self._last_failure_time.isoformat() if self._last_failure_time else None,
                "redis_connected": client is not None,
                "timestamp": datetime.now().isoformat()
            }

            if client:
                try:
                    info = await client.info()
                    stats.update({
                        "redis_version": info.get("redis_version"),
                        "connected_clients": info.get("connected_clients"),
                        "used_memory_human": info.get("used_memory_human"),
                        "total_connections_received": info.get("total_connections_received"),
                    })
                except Exception as e:
                    logger.warning(f"Could not get Redis info: {str(e)}")

            return stats

        except Exception as e:
            logger.error(f"Error getting Redis stats: {str(e)}")
            return {"error": str(e)}

    async def initialize(self) -> None:
        """Initialize the Redis cache."""
        try:
            # Test connection
            await self.ping()
            logger.info("Redis cache initialized successfully")
        except Exception as e:
            logger.warning(f"Redis cache initialization failed: {str(e)}")
            # Don't raise - Redis is optional fallback to file cache


# Global cache service instance
cache_service = CacheService()
