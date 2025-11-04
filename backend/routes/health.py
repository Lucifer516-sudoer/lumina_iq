"""
Health check routes for monitoring and production deployment.
Provides async endpoints for liveness, readiness, detailed health, and metrics.
"""

import time
from fastapi import APIRouter, Response, HTTPException
from fastapi.responses import PlainTextResponse

from services.health_service import health_service
from utils.logger import get_logger
from utils.logging_config import set_request_id, clear_request_id

logger = get_logger("health_routes")

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live", response_model=None)
async def health_live():
    """
    Liveness probe endpoint.

    Returns a simple response indicating the service is running.
    Used by load balancers and orchestrators (like Kubernetes) to determine
    if the application needs to be restarted.

    Returns:
        dict: Simple liveness status
    """
    # Set request ID for tracing
    request_id = set_request_id()

    logger.debug(f"Liveness probe requested - endpoint: /health/live")

    try:
        health_data = await health_service.check_liveness()

        logger.debug(f"Liveness check completed - status: {health_data.get('status')}, uptime_seconds: {health_data.get('uptime_seconds')}")

        return health_data
    except Exception as e:
        logger.error(f"Liveness check failed - error_type: {type(e).__name__}, error_message: {str(e)}")
        raise HTTPException(status_code=503, detail="Service unhealthy")
    finally:
        clear_request_id()


@router.get("/ready", response_model=None)
async def health_ready():
    """
    Readiness probe endpoint.

    Checks if the service is ready to serve requests by verifying all
    dependencies (Redis, Qdrant, Celery) are healthy.

    Returns:
        dict: Readiness status with detailed dependency information
    """
    # Set request ID for tracing
    request_id = set_request_id()

    logger.debug(f"Readiness probe requested - endpoint: /health/ready")

    try:
        health_data = await health_service.check_readiness()

        # Log readiness status with detailed information
        dependencies = health_data.get("dependencies", {})
        checks_passed = len([d for d in dependencies.values() if d.get("healthy", False)])
        checks_total = len(dependencies)
        logger.info(f"Readiness check completed - status: {health_data.get('status', 'unknown')}, checks_passed: {checks_passed}, checks_total: {checks_total}")

        # Return appropriate HTTP status based on readiness
        if health_data["status"] == "ready":
            return health_data
        else:
            # Return 503 for degraded/unhealthy but still provide info
            raise HTTPException(status_code=503, detail=health_data)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Readiness check failed - error_type: {type(e).__name__}, error_message: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail={
                "status": "unhealthy",
                "service": "learning-app-api",
                "error": str(e)
            }
        )
    finally:
        clear_request_id()


@router.get("/detailed", response_model=None)
async def health_detailed():
    """
    Comprehensive health check endpoint.

    Provides detailed information about all services, cache statistics,
    worker information, and system metrics. Useful for monitoring dashboards
    and detailed diagnostics.

    Returns:
        dict: Comprehensive health information
    """
    try:
        health_data = await health_service.get_detailed_health()

        # Return appropriate HTTP status based on health
        if health_data["status"] in ["ready", "healthy"]:
            return health_data
        else:
            raise HTTPException(status_code=503, detail=health_data)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Detailed health check failed: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail={
                "status": "unhealthy",
                "service": "learning-app-api",
                "error": str(e)
            }
        )


@router.get("/metrics", response_class=PlainTextResponse)
async def metrics():
    """
    Prometheus metrics endpoint.

    Returns metrics in Prometheus format for monitoring and alerting.
    Includes health status, service latencies, cache statistics, queue lengths,
    and performance metrics.

    Returns:
        str: Prometheus-formatted metrics
    """
    try:
        start_time = time.time()
        metrics_data = await health_service.get_prometheus_metrics()
        response_time = (time.time() - start_time) * 1000

        # Record response time for internal metrics
        health_service.record_response_time(response_time)

        return Response(
            content=metrics_data,
            media_type="text/plain; version=0.0.4; charset=utf-8"
        )
    except Exception as e:
        logger.error(f"Metrics collection failed: {str(e)}")
        health_service.record_error(500)
        raise HTTPException(
            status_code=503,
            detail=f"Failed to collect metrics: {str(e)}"
        )


# Additional health endpoints for compatibility

@router.head("/live")
async def health_live_head():
    """HEAD version of liveness probe for load balancer compatibility."""
    return Response(status_code=200)


@router.head("/ready")
async def health_ready_head():
    """HEAD version of readiness probe for load balancer compatibility."""
    health_data = await health_service.check_readiness()
    status_code = 200 if health_data["status"] == "ready" else 503
    return Response(status_code=status_code)