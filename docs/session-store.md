# Session Store Documentation

## Overview

The Session Store provides a persistence layer for managing chatbot session state across requests. It supports both in-memory (for development) and Redis-backed (for production) implementations.

## Architecture

### Abstract Base Class

`SessionStore` defines the interface that all session store implementations must follow:

- `save(session_id, state, ttl)` - Save session state with TTL
- `load(session_id)` - Load session state
- `delete(session_id)` - Delete session state
- `exists(session_id)` - Check if session exists

All methods are async and use `await`.

### Implementations

#### InMemorySessionStore

- Stores sessions in a Python dictionary
- Suitable for development and single-process deployments
- Automatically cleans up expired sessions
- No external dependencies

#### RedisSessionStore

- Stores sessions in Redis with native TTL support
- Suitable for production and distributed deployments
- Supports connection pooling and async operations
- Uses `redis.asyncio` for async support

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `VALERIE_SESSION_STORE` | Store type: `memory` or `redis` | `memory` |
| `VALERIE_SESSION_REDIS_URL` | Redis connection URL | `redis://localhost:6379` |
| `VALERIE_SESSION_TTL` | Session TTL in seconds | `3600` (1 hour) |
| `VALERIE_SESSION_PREFIX` | Redis key prefix | `valerie:session:` |

### Factory Function

Use `get_session_store()` to automatically create the appropriate store based on environment variables:

```python
from valerie.infrastructure import get_session_store, get_default_ttl

# Get configured store
store = get_session_store()

# Get configured TTL
ttl = get_default_ttl()
```

## Usage Examples

### Basic Usage

```python
from valerie.infrastructure import InMemorySessionStore

# Create store
store = InMemorySessionStore()

# Save session
session_id = "user-123-session"
state = {
    "user_id": "user-123",
    "conversation_step": 1,
    "intent": "supplier_search"
}
await store.save(session_id, state, ttl=3600)

# Load session
loaded_state = await store.load(session_id)

# Check existence
exists = await store.exists(session_id)

# Delete session
await store.delete(session_id)
```

### Redis Store

```python
from valerie.infrastructure import RedisSessionStore

# Create Redis store
store = RedisSessionStore(
    redis_url="redis://localhost:6379",
    prefix="chatbot:session:"
)

# Use same API as InMemorySessionStore
await store.save(session_id, state, ttl=7200)
loaded = await store.load(session_id)

# Close connection when done
await store.close()
```

### Using Factory Function

```python
import os
from valerie.infrastructure import get_session_store, get_default_ttl

# Configure via environment
os.environ["VALERIE_SESSION_STORE"] = "redis"
os.environ["VALERIE_SESSION_REDIS_URL"] = "redis://localhost:6379"
os.environ["VALERIE_SESSION_TTL"] = "7200"

# Get configured store
store = get_session_store()
ttl = get_default_ttl()

# Use store
await store.save(session_id, state, ttl=ttl)
```

## File Locations

- **Implementation**: `src/valerie/infrastructure/session_store.py`
- **Tests**: `tests/unit/test_session_store.py`
- **Examples**: `examples/session_store_usage.py`

## Testing

Run the test suite:

```bash
# Run session store tests only
pytest tests/unit/test_session_store.py -v

# Run with coverage
pytest tests/unit/test_session_store.py --cov=valerie.infrastructure.session_store
```

All 32 tests pass successfully:
- 1 abstract interface test
- 11 InMemorySessionStore tests
- 10 RedisSessionStore tests
- 6 factory function tests
- 3 helper function tests
- 2 integration tests

## Features

### InMemorySessionStore Features

- Automatic expiry handling
- Opportunistic cleanup of expired sessions
- Support for complex state objects (nested dicts, lists, etc.)
- Thread-safe for async operations
- No external dependencies

### RedisSessionStore Features

- Native Redis TTL support
- Connection pooling via `redis.asyncio`
- JSON serialization/deserialization
- Configurable key prefixes for namespacing
- Graceful connection management with `close()` method

## Implementation Details

### State Serialization

- InMemorySessionStore: Stores Python dict objects directly
- RedisSessionStore: Uses JSON serialization via `json.dumps()`/`json.loads()`

### TTL Management

- InMemorySessionStore: Manual tracking with `time.time()` and expiry timestamps
- RedisSessionStore: Native Redis SETEX command with automatic expiry

### Async Support

All methods are async and should be called with `await`:

```python
# Correct
state = await store.load(session_id)

# Incorrect - will return a coroutine object
state = store.load(session_id)  # Wrong!
```

## Production Recommendations

1. **Use Redis in Production**: RedisSessionStore is recommended for production deployments to support:
   - Multiple application instances
   - Session persistence across restarts
   - Distributed deployments

2. **Set Appropriate TTLs**: Configure session TTL based on your use case:
   - Short sessions (15-30 min): Casual browsing
   - Medium sessions (1-2 hours): Active conversations
   - Long sessions (4-8 hours): Complex workflows

3. **Monitor Redis**: Set up monitoring for:
   - Memory usage
   - Key eviction rate
   - Connection pool saturation

4. **Key Prefixes**: Use meaningful prefixes to:
   - Namespace sessions by environment (dev, staging, prod)
   - Separate different chatbot instances
   - Enable selective key deletion

## Migration from In-Memory to Redis

```python
# Development configuration
os.environ["VALERIE_SESSION_STORE"] = "memory"

# Production configuration
os.environ["VALERIE_SESSION_STORE"] = "redis"
os.environ["VALERIE_SESSION_REDIS_URL"] = "redis://prod-redis:6379"
os.environ["VALERIE_SESSION_PREFIX"] = "prod:chatbot:session:"

# Code remains the same
store = get_session_store()
```

No code changes required - just update environment variables!
