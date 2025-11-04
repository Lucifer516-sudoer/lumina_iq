#!/bin/bash
# Startup script for Learning App backend
# Supports both Docker and traditional server deployments

set -e

# Configuration
ENVIRONMENT=${ENVIRONMENT:-production}
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="${PROJECT_ROOT}/backend"
LOG_DIR="${PROJECT_ROOT}/logs"
PID_DIR="/var/run/learning-app"

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

# Check if running as root (for system installation)
check_permissions() {
    if [[ $EUID -eq 0 ]]; then
        log_warn "Running as root - this should only be done in containers"
    fi
}

# Create necessary directories
create_directories() {
    log_info "Creating necessary directories..."

    # Create log directory with proper permissions
    mkdir -p "${LOG_DIR}"
    mkdir -p "${LOG_DIR}/gunicorn"
    mkdir -p "${LOG_DIR}/celery"
    mkdir -p "${LOG_DIR}/app"

    # Create PID directory (system location)
    if [[ $EUID -eq 0 ]]; then
        mkdir -p "${PID_DIR}"
        chown www-data:www-data "${PID_DIR}" 2>/dev/null || true
    fi

    # Set permissions
    chmod 755 "${LOG_DIR}"
    chmod 755 "${LOG_DIR}/gunicorn"
    chmod 755 "${LOG_DIR}/celery"
    chmod 755 "${LOG_DIR}/app"
}

# Wait for dependencies
wait_for_service() {
    local service=$1
    local host=$2
    local port=$3
    local timeout=${4:-30}

    log_info "Waiting for ${service} at ${host}:${port}..."

    local count=0
    while ! nc -z "${host}" "${port}" 2>/dev/null; do
        if [[ $count -ge $timeout ]]; then
            log_error "${service} is not available at ${host}:${port} after ${timeout} seconds"
            return 1
        fi
        count=$((count + 1))
        sleep 1
    done

    log_info "${service} is ready"
}

# Start Redis if not running
start_redis() {
    if ! pgrep -f redis-server > /dev/null; then
        log_info "Starting Redis..."
        if command -v redis-server &> /dev/null; then
            redis-server --daemonize yes --port 6379
        else
            log_warn "Redis not found, assuming it's running in Docker"
        fi
    else
        log_info "Redis is already running"
    fi
}

# Start Qdrant if not running
start_qdrant() {
    if ! pgrep -f qdrant > /dev/null; then
        log_info "Starting Qdrant..."
        if command -v qdrant &> /dev/null; then
            # This is a simplified startup - adjust for your Qdrant installation
            nohup qdrant --uri "http://localhost:6333" > "${LOG_DIR}/qdrant.log" 2>&1 &
        else
            log_warn "Qdrant not found, assuming it's running in Docker"
        fi
    else
        log_info "Qdrant is already running"
    fi
}

# Pre-deployment checks
pre_deployment_checks() {
    log_info "Running pre-deployment checks..."

    # Check if port is available
    if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null; then
        log_error "Port 8000 is already in use"
        exit 1
    fi

    # Check environment file
    local env_file="${BACKEND_DIR}/.env.${ENVIRONMENT}"
    if [[ ! -f "${env_file}" ]]; then
        log_warn "Environment file ${env_file} not found, using default"
    else
        log_info "Using environment file: ${env_file}"
    fi

    # Wait for Redis
    wait_for_service "Redis" "localhost" "6379" || true

    # Wait for Qdrant
    wait_for_service "Qdrant" "localhost" "6333" || true
}

# Start the application
start_application() {
    log_info "Starting Learning App backend in ${ENVIRONMENT} environment..."

    cd "${BACKEND_DIR}"

    # Set environment variables
    export ENVIRONMENT="${ENVIRONMENT}"
    export PYTHONPATH="${BACKEND_DIR}"

    # Start with gunicorn
    local gunicorn_cmd=(
        gunicorn
        --config gunicorn.conf.py
        --pid /var/run/gunicorn/learning-app.pid
        --log-file "${LOG_DIR}/gunicorn/app.log"
        --access-logfile "${LOG_DIR}/gunicorn/access.log"
        main:app
    )

    log_info "Starting Gunicorn with command: ${gunicorn_cmd[*]}"

    # Start gunicorn
    if [[ $EUID -eq 0 ]]; then
        # Running as root, switch to www-data user
        su -c "${gunicorn_cmd[*]}" www-data
    else
        "${gunicorn_cmd[@]}"
    fi
}

# Main startup sequence
main() {
    log_info "Learning App Backend Startup Script"
    log_info "Environment: ${ENVIRONMENT}"
    log_info "Project Root: ${PROJECT_ROOT}"

    check_permissions
    create_directories
    pre_deployment_checks

    # Start services if not in Docker
    if [[ ! -f /.dockerenv ]]; then
        start_redis
        start_qdrant
    fi

    start_application

    log_info "Learning App backend started successfully"
    log_info "Check logs at: ${LOG_DIR}"
    log_info "Health check: curl http://localhost:8000/health"
}

# Handle script arguments
case "${1:-}" in
    "status")
        if pgrep -f gunicorn > /dev/null; then
            log_info "Learning App backend is running"
            exit 0
        else
            log_error "Learning App backend is not running"
            exit 1
        fi
        ;;
    "stop")
        log_info "Stopping Learning App backend..."
        if [[ -f /var/run/gunicorn/learning-app.pid ]]; then
            kill -TERM "$(cat /var/run/gunicorn/learning-app.pid)" 2>/dev/null || true
            sleep 5
            kill -KILL "$(cat /var/run/gunicorn/learning-app.pid)" 2>/dev/null || true
            rm -f /var/run/gunicorn/learning-app.pid
        else
            pkill -f gunicorn || true
        fi

        # Stop Redis if started by this script
        pkill -f redis-server || true

        log_info "Learning App backend stopped"
        exit 0
        ;;
    *)
        main
        ;;
esac