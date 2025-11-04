# Gunicorn configuration for production deployment
# Supports 1000+ concurrent users through multi-process scaling

import os
import multiprocessing
from config.settings import settings

# Server socket
bind = f"{settings.HOST}:{settings.PORT}"
backlog = 2048

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1  # (2 * CPU cores + 1) for optimal performance
worker_class = "uvicorn.workers.UvicornWorker"  # Use Uvicorn workers for async support
worker_connections = 1000  # Max connections per worker

# Threads per worker (for Uvicorn workers)
threads = 4  # 4 threads per worker for I/O bound tasks

# Timeout settings
timeout = 30  # Worker timeout in seconds
keepalive = 10  # Keep-alive timeout
graceful_timeout = 30  # Graceful shutdown timeout

# Process management
preload_app = True  # Preload application in master process
max_requests = 1000  # Max requests per worker before restart
max_requests_jitter = 50  # Jitter for max_requests to avoid thundering herd
worker_tmp_dir = "/dev/shm"  # Use shared memory for temp files (Linux)

# Logging
loglevel = settings.LOG_LEVEL.lower()
accesslog = "/var/log/gunicorn/access.log"
errorlog = "/var/log/gunicorn/error.log"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = "learning_app_api"

# Server mechanics
daemon = False  # Run in foreground for containerization
pidfile = "/var/run/gunicorn/gunicorn.pid"
user = "www-data" if os.path.exists("/etc/passwd") else None
group = "www-data" if os.path.exists("/etc/passwd") else None

# SSL (if needed)
# keyfile = "/path/to/ssl/private.key"
# certfile = "/path/to/ssl/certificate.crt"

# Health check
def on_starting(server):
    """Called just before the master process is initialized."""
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Starting Gunicorn server with {workers} workers")

def worker_int(worker):
    """Called when a worker is initialized."""
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Worker {worker.pid} initialized")

def worker_exit(server, worker):
    """Called when a worker exits."""
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Worker {worker.pid} exited")

# Hook functions
on_starting = on_starting
worker_int = worker_int
worker_exit = worker_exit