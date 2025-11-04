# Redis Configuration Guide

## Overview

Lumina IQ uses Redis for:
- **Caching**: Embeddings, retrieval results, API responses
- **Task Queue**: Celery background tasks
- **Session Management**: User sessions and temporary data

## Configuration Options

### 1. Redis Cloud (Production - Recommended)

**Format:**
```env
REDIS_URL=redis://default:<password>@<hostname>:<port>
CELERY_BROKER_URL=redis://default:<password>@<hostname>:<port>/1
CELERY_RESULT_BACKEND=redis://default:<password>@<hostname>:<port>/2
```

**Example:**
```env
REDIS_URL=redis://default:mySecretPassword123@redis-13314.c301.ap-south-1-1.ec2.redns.redis-cloud.com:13314
CELERY_BROKER_URL=redis://default:mySecretPassword123@redis-13314.c301.ap-south-1-1.ec2.redns.redis-cloud.com:13314/1
CELERY_RESULT_BACKEND=redis://default:mySecretPassword123@redis-13314.c301.ap-south-1-1.ec2.redns.redis-cloud.com:13314/2
```

**How to Get Redis Cloud Password:**
1. Log in to [Redis Cloud Console](https://app.redislabs.com/)
2. Select your database
3. Go to **Configuration** tab
4. Copy the **Default user password**
5. Update your `.env` file with the password

### 2. Local Redis (Development)

**Without Authentication:**
```env
REDIS_URL=redis://localhost:6379
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2
```

**With Authentication:**
```env
REDIS_URL=redis://default:your_password@localhost:6379
CELERY_BROKER_URL=redis://default:your_password@localhost:6379/1
CELERY_RESULT_BACKEND=redis://default:your_password@localhost:6379/2
```

**Install Redis Locally:**

**Windows:**
```bash
# Using Chocolatey
choco install redis-64

# Or using WSL
wsl sudo apt-get install redis-server
```

**Linux/macOS:**
```bash
# Ubuntu/Debian
sudo apt-get install redis-server

# macOS
brew install redis

# Start Redis
redis-server
```

### 3. Docker Redis (Development)

**Start Redis container:**
```bash
docker run -d \
  --name redis \
  -p 6379:6379 \
  redis:7-alpine redis-server --requirepass mypassword
```

**Configuration:**
```env
REDIS_URL=redis://default:mypassword@localhost:6379
CELERY_BROKER_URL=redis://default:mypassword@localhost:6379/1
CELERY_RESULT_BACKEND=redis://default:mypassword@localhost:6379/2
```

## Testing Redis Connection

### Method 1: Using redis-cli

```bash
# Without password
redis-cli -h <hostname> -p <port> ping

# With password
redis-cli -h <hostname> -p <port> -a <password> ping

# Should return: PONG
```

### Method 2: Using Python

```python
import redis

# Create connection
client = redis.from_url("redis://default:<password>@<hostname>:<port>")

# Test connection
print(client.ping())  # Should return True
```

## Troubleshooting

### Error: "Authentication required"

**Cause:** Redis URL is missing password

**Solution:** Add password to REDIS_URL
```env
# ❌ Wrong
REDIS_URL=redis://hostname:port

# ✅ Correct
REDIS_URL=redis://default:password@hostname:port
```

### Error: "Connection refused"

**Cause:** Redis server is not running or not accessible

**Solutions:**
1. Check if Redis server is running: `redis-cli ping`
2. Check firewall rules allow connection to port
3. Verify hostname and port are correct
4. For Redis Cloud, check if your IP is whitelisted

### Error: "Timeout"

**Cause:** Network issues or Redis server overloaded

**Solutions:**
1. Check network connectivity
2. Increase timeout in settings
3. Check Redis Cloud instance is not suspended

## Fallback Behavior

**Without Redis:**
- ✅ Application starts successfully
- ⚠️ Caching is disabled (performance degraded)
- ⚠️ Background tasks may not work
- ✅ Core RAG functionality works

**The backend continues to function without Redis but with reduced performance.**

## Production Best Practices

1. **Always use authentication** in production
2. **Use Redis Cloud** or managed Redis service
3. **Enable SSL/TLS** for encrypted connections
4. **Set up monitoring** for Redis health
5. **Configure backups** for Redis data
6. **Use separate databases** for cache (0), broker (1), and results (2)
7. **Set appropriate TTL** for cached data
8. **Monitor memory usage** to avoid OOM errors

## Configuration Validation

After updating `.env`, verify configuration:

```bash
# Start backend
uv run backend/run.py

# Check logs for:
# ✅ "Redis cache service initialized successfully"
# ❌ "Failed to initialize Redis cache service: Authentication required"
```

## Environment Variables Reference

| Variable | Description | Example |
|----------|-------------|---------|
| `REDIS_URL` | Main Redis connection URL | `redis://default:pass@host:6379` |
| `REDIS_CACHE_DB` | Database number for caching | `0` |
| `REDIS_TASK_DB` | Database number for tasks | `1` |
| `CELERY_BROKER_URL` | Celery message broker URL | `redis://default:pass@host:6379/1` |
| `CELERY_RESULT_BACKEND` | Celery result storage URL | `redis://default:pass@host:6379/2` |
| `CACHE_TTL_SECONDS` | Cache expiration time | `3600` (1 hour) |
| `CACHE_EMBEDDINGS` | Enable embedding caching | `true` |
| `CACHE_QUERY_RESULTS` | Enable query result caching | `true` |

## Support

For issues with Redis configuration:
1. Check this guide first
2. Review error logs in `backend/logs/`
3. Verify Redis credentials in Redis Cloud console
4. Test connection manually using redis-cli
5. Check network/firewall settings
