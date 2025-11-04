"""
Health Service for Lumina IQ RAG Backend.

Provides comprehensive monitoring and health checks for all system dependencies.
"""

import asyncio
import time
from typing import Dict, Any
from datetime import datetime

from config.settings import settings
from utils.logger import get_logger
from .cache_service import cache_service
from .qdrant_service import qdrant_service

logger = get_logger("health_service")


class HealthService:
    """Comprehensive health monitoring service."""

    def __init__(self):
        self._start_time = time.time()
        self._response_times = []
        self._error_counts = {"4xx": 0, "5xx": 0}

    async def check_liveness(self) -> Dict[str, Any]:
        """Liveness probe - check if service is running."""
        return {
            "status": "alive",
            "service": "lumina_iq_backend",
            "timestamp": datetime.now().isoformat(),
            "uptime_seconds": int(time.time() - self._start_time),
        }

    async def _check_redis_health(self) -> Dict[str, Any]:
        """Check Redis health."""
        try:
            if not cache_service.is_initialized or not cache_service.redis_client:
                return {
                    "status": "unhealthy",
                    "available": False,
                    "error": "Redis not initialized",
                    "timestamp": datetime.now().isoformat()
                }

            # Test connection with ping
            start = time.time()
            await cache_service.redis_client.ping()
            latency = (time.time() - start) * 1000

            return {
                "status": "healthy",
                "available": True,
                "latency_ms": round(latency, 2),
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.warning(f"Redis health check failed: {str(e)}")
            return {
                "status": "unhealthy",
                "available": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    async def _check_qdrant_health(self) -> Dict[str, Any]:
        """Check Qdrant health."""
        try:
            if not qdrant_service.is_initialized or not qdrant_service.client:
                return {
                    "status": "unhealthy",
                    "available": False,
                    "error": "Qdrant not initialized",
                    "timestamp": datetime.now().isoformat()
                }

            # Test connection with collection info
            start = time.time()
            collection_info = await qdrant_service.get_collection_info()
            latency = (time.time() - start) * 1000

            return {
                "status": "healthy",
                "available": True,
                "latency_ms": round(latency, 2),
                "points_count": collection_info.get("points_count", 0),
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.warning(f"Qdrant health check failed: {str(e)}")
            return {
                "status": "unhealthy",
                "available": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    async def check_readiness(self) -> Dict[str, Any]:
        """Readiness probe - check if service is ready to serve requests."""
        try:
            # Perform health checks concurrently
            redis_health, qdrant_health = await asyncio.gather(
                self._check_redis_health(),
                self._check_qdrant_health(),
                return_exceptions=True
            )

            # Handle exceptions from gather
            if isinstance(redis_health, Exception):
                redis_health = {
                    "status": "unhealthy",
                    "available": False,
                    "error": str(redis_health),
                    "timestamp": datetime.now().isoformat()
                }

            if isinstance(qdrant_health, Exception):
                qdrant_health = {
                    "status": "unhealthy",
                    "available": False,
                    "error": str(qdrant_health),
                    "timestamp": datetime.now().isoformat()
                }

            # Determine overall readiness
            all_healthy = all([
                redis_health.get("status") == "healthy",
                qdrant_health.get("status") == "healthy",
            ])

            return {
                "status": "ready" if all_healthy else "degraded",
                "service": "lumina_iq_backend",
                "dependencies": {
                    "redis": redis_health,
                    "qdrant": qdrant_health,
                },
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Readiness check failed: {str(e)}")
            return {
                "status": "unhealthy",
                "service": "lumina_iq_backend",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    async def get_detailed_health(self) -> Dict[str, Any]:
        """Comprehensive health check with detailed information."""
        try:
            readiness = await self.check_readiness()
            cache_stats = await cache_service.get_stats()

            # Get collection info from Qdrant
            qdrant_info = {}
            try:
                if qdrant_service.is_initialized:
                    qdrant_info = await qdrant_service.get_collection_info()
            except Exception as e:
                logger.warning(f"Failed to get Qdrant info: {str(e)}")

            return {
                "status": readiness["status"],
                "service": "lumina_iq_backend",
                "uptime_seconds": int(time.time() - self._start_time),
                "readiness": readiness,
                "cache": cache_stats,
                "qdrant": qdrant_info,
                "performance": {
                    "avg_response_time_ms": (
                        sum(self._response_times) / len(self._response_times)
                        if self._response_times else 0
                    ),
                    "error_counts": self._error_counts,
                },
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Detailed health check failed: {str(e)}")
            return {
                "status": "unhealthy",
                "service": "lumina_iq_backend",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    async def get_prometheus_metrics(self) -> str:
        """Generate Prometheus-compatible metrics."""
        try:
            readiness = await self.check_readiness()
            cache_stats = await cache_service.get_stats()

            metrics_lines = [
                "# HELP lumina_api_health_status Overall API health status (1=healthy, 0=unhealthy)",
                "# TYPE lumina_api_health_status gauge"
            ]

            # Overall health
            health_value = 1 if readiness["status"] == "ready" else 0
            metrics_lines.append(f'lumina_api_health_status {health_value}')

            # Service health metrics
            for service_name, service_health in readiness.get("dependencies", {}).items():
                status_value = 1 if service_health.get("status") == "healthy" else 0
                metrics_lines.extend([
                    f'# HELP lumina_api_{service_name}_health {service_name} service health',
                    f'# TYPE lumina_api_{service_name}_health gauge',
                    f'lumina_api_{service_name}_health {status_value}'
                ])

                # Latency metrics
                latency = service_health.get("latency_ms")
                if latency is not None:
                    metrics_lines.extend([
                        f'# HELP lumina_api_{service_name}_latency_ms {service_name} latency in ms',
                        f'# TYPE lumina_api_{service_name}_latency_ms gauge',
                        f'lumina_api_{service_name}_latency_ms {latency}'
                    ])

            # Cache metrics
            if cache_stats.get("status") == "connected":
                hit_rate = cache_stats.get("hit_rate", 0)
                metrics_lines.extend([
                    '# HELP lumina_api_cache_hit_rate Cache hit rate percentage',
                    '# TYPE lumina_api_cache_hit_rate gauge',
                    f'lumina_api_cache_hit_rate {hit_rate}'
                ])

            # Performance metrics
            if self._response_times:
                avg_response_time = sum(self._response_times) / len(self._response_times)
                metrics_lines.extend([
                    '# HELP lumina_api_avg_response_time_ms Average response time in ms',
                    '# TYPE lumina_api_avg_response_time_ms gauge',
                    f'lumina_api_avg_response_time_ms {avg_response_time}'
                ])

            # Error counts
            for error_type, count in self._error_counts.items():
                metrics_lines.extend([
                    f'# HELP lumina_api_{error_type}_errors Number of {error_type} errors',
                    f'# TYPE lumina_api_{error_type}_errors counter',
                    f'lumina_api_{error_type}_errors {count}'
                ])

            # Uptime
            uptime = int(time.time() - self._start_time)
            metrics_lines.extend([
                '# HELP lumina_api_uptime_seconds Service uptime in seconds',
                '# TYPE lumina_api_uptime_seconds counter',
                f'lumina_api_uptime_seconds {uptime}'
            ])

            return "\n".join(metrics_lines) + "\n"

        except Exception as e:
            logger.error(f"Failed to generate Prometheus metrics: {str(e)}")
            return f"# Error generating metrics: {str(e)}\n"

    def record_response_time(self, response_time_ms: float):
        """Record a response time for metrics."""
        self._response_times.append(response_time_ms)
        # Keep only last 1000 measurements
        if len(self._response_times) > 1000:
            self._response_times = self._response_times[-1000:]

    def record_error(self, status_code: int):
        """Record an error for metrics."""
        if 400 <= status_code < 500:
            self._error_counts["4xx"] += 1
        elif status_code >= 500:
            self._error_counts["5xx"] += 1


# Global singleton instance
health_service = HealthService()
