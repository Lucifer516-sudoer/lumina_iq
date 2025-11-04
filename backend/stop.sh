#!/bin/bash
# Shutdown script for Learning App backend

set -e

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="${PROJECT_ROOT}/backend"
LOG_DIR="${PROJECT_ROOT}/logs"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Graceful shutdown function
graceful_shutdown() {
    local service_name=$1
    local pid_file=$2
    local timeout=${3:-30}

    log_info "Gracefully shutting down ${service_name}..."

    if [[ -f "${pid_file}" ]]; then
        local pid=$(cat "${pid_file}")

        if kill -TERM "${pid}" 2>/dev/null; then
            log_info "Sent SIGTERM to ${service_name} (PID: ${pid})"

            # Wait for graceful shutdown
            local count=0
            while kill -0 "${pid}" 2>/dev/null && [[ $count -lt $timeout ]]; do
                sleep 1
                count=$((count + 1))
            done

            if kill -0 "${pid}" 2>/dev/null; then
                log_warn "${service_name} did not shutdown gracefully, sending SIGKILL"
                kill -KILL "${pid}" 2>/dev/null || true
                sleep 2
            else
                log_info "${service_name} shutdown gracefully"
            fi
        else
            log_warn "PID ${pid} not found or already dead"
        fi

        rm -f "${pid_file}"
    else
        log_warn "PID file ${pid_file} not found"
    fi
}

# Stop all services
stop_all_services() {
    log_info "Stopping all Learning App services..."

    # Stop Gunicorn
    graceful_shutdown "Gunicorn" "/var/run/gunicorn/learning-app.pid" 30

    # Stop any remaining gunicorn processes
    if pgrep -f "gunicorn.*main:app" > /dev/null; then
        log_warn "Found remaining gunicorn processes, killing..."
        pkill -TERM -f "gunicorn.*main:app" || true
        sleep 5
        pkill -KILL -f "gunicorn.*main:app" || true
    fi

    # Stop Celery workers
    if pgrep -f "celery.*worker" > /dev/null; then
        log_info "Stopping Celery workers..."
        pkill -TERM -f "celery.*worker" || true
        sleep 10
        pkill -KILL -f "celery.*worker" || true
    fi

    # Stop Redis (only if started by our scripts)
    if pgrep -f "redis-server" > /dev/null; then
        # Check if Redis was started by our startup script
        if [[ -f "/var/run/redis.pid" ]] && pgrep -F "/var/run/redis.pid" > /dev/null 2>&1; then
            log_info "Stopping Redis..."
            kill -TERM "$(cat /var/run/redis.pid)" 2>/dev/null || true
            sleep 5
        fi
    fi

    # Stop Qdrant (only if started by our scripts)
    if pgrep -f "qdrant" > /dev/null; then
        log_info "Stopping Qdrant..."
        pkill -TERM -f "qdrant" || true
        sleep 5
        pkill -KILL -f "qdrant" || true
    fi

    log_info "All services stopped"
}

# Clean up function
cleanup() {
    log_info "Cleaning up temporary files..."

    # Remove PID files
    rm -f /var/run/gunicorn/learning-app.pid
    rm -f /var/run/redis.pid
    rm -f /var/run/qdrant.pid

    # Remove socket files if any
    rm -f /tmp/learning-app.sock

    log_info "Cleanup completed"
}

# Main shutdown sequence
main() {
    log_info "Learning App Backend Shutdown Script"
    log_info "Project Root: ${PROJECT_ROOT}"

    stop_all_services
    cleanup

    log_info "Learning App backend shutdown completed successfully"
}

# Handle script arguments
case "${1:-}" in
    "force")
        log_warn "Force shutdown requested"
        # Kill all processes immediately
        pkill -KILL -f "gunicorn.*main:app" || true
        pkill -KILL -f "celery.*worker" || true
        pkill -KILL -f "redis-server" || true
        pkill -KILL -f "qdrant" || true
        cleanup
        log_info "Force shutdown completed"
        ;;
    *)
        main
        ;;
esac