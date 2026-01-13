"""Session persistence layer for chatbot state management.

This module provides abstract and concrete implementations for session storage,
supporting both in-memory (for development) and Redis-backed (for production)
persistence strategies.
"""

import json
import os
import time
from abc import ABC, abstractmethod

from redis import asyncio as aioredis


class SessionStore(ABC):
    """Abstract base class for session storage implementations."""

    @abstractmethod
    async def save(self, session_id: str, state: dict, ttl: int = 3600) -> None:
        """Save session state with TTL.

        Args:
            session_id: Unique identifier for the session
            state: State dictionary to persist
            ttl: Time-to-live in seconds (default: 3600)
        """
        pass

    @abstractmethod
    async def load(self, session_id: str) -> dict | None:
        """Load session state.

        Args:
            session_id: Unique identifier for the session

        Returns:
            State dictionary if found, None otherwise
        """
        pass

    @abstractmethod
    async def delete(self, session_id: str) -> None:
        """Delete session state.

        Args:
            session_id: Unique identifier for the session
        """
        pass

    @abstractmethod
    async def exists(self, session_id: str) -> bool:
        """Check if session exists.

        Args:
            session_id: Unique identifier for the session

        Returns:
            True if session exists, False otherwise
        """
        pass


class InMemorySessionStore(SessionStore):
    """In-memory session store for development and testing.

    This implementation stores sessions in a dictionary with expiry times.
    Not suitable for production use in multi-process or distributed environments.
    """

    def __init__(self) -> None:
        """Initialize the in-memory store."""
        self._store: dict[str, tuple[dict, float]] = {}  # (state, expiry_time)

    async def save(self, session_id: str, state: dict, ttl: int = 3600) -> None:
        """Save session state with TTL."""
        expiry_time = time.time() + ttl
        self._store[session_id] = (state, expiry_time)
        # Clean up expired sessions opportunistically
        await self._cleanup_expired()

    async def load(self, session_id: str) -> dict | None:
        """Load session state."""
        if session_id not in self._store:
            return None

        state, expiry_time = self._store[session_id]

        # Check if expired
        if time.time() > expiry_time:
            del self._store[session_id]
            return None

        return state

    async def delete(self, session_id: str) -> None:
        """Delete session state."""
        if session_id in self._store:
            del self._store[session_id]

    async def exists(self, session_id: str) -> bool:
        """Check if session exists."""
        if session_id not in self._store:
            return False

        _, expiry_time = self._store[session_id]

        # Check if expired
        if time.time() > expiry_time:
            del self._store[session_id]
            return False

        return True

    async def _cleanup_expired(self) -> None:
        """Remove expired sessions from the store."""
        current_time = time.time()
        expired_keys = [
            key for key, (_, expiry_time) in self._store.items() if current_time > expiry_time
        ]
        for key in expired_keys:
            del self._store[key]


class RedisSessionStore(SessionStore):
    """Redis-backed session store for production use.

    This implementation uses Redis for persistent, distributed session storage
    with automatic TTL handling.
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        prefix: str = "valerie:session:",
    ) -> None:
        """Initialize Redis session store.

        Args:
            redis_url: Redis connection URL
            prefix: Key prefix for namespacing sessions
        """
        self.redis_url = redis_url
        self.prefix = prefix
        self._client: aioredis.Redis | None = None

    async def _get_client(self) -> aioredis.Redis:
        """Get or create Redis client."""
        if self._client is None:
            self._client = await aioredis.from_url(
                self.redis_url, encoding="utf-8", decode_responses=True
            )
        return self._client

    def _make_key(self, session_id: str) -> str:
        """Create prefixed key for session ID."""
        return f"{self.prefix}{session_id}"

    async def save(self, session_id: str, state: dict, ttl: int = 3600) -> None:
        """Save session state with TTL."""
        client = await self._get_client()
        key = self._make_key(session_id)
        serialized = json.dumps(state)
        await client.setex(key, ttl, serialized)

    async def load(self, session_id: str) -> dict | None:
        """Load session state."""
        client = await self._get_client()
        key = self._make_key(session_id)
        serialized = await client.get(key)

        if serialized is None:
            return None

        return json.loads(serialized)

    async def delete(self, session_id: str) -> None:
        """Delete session state."""
        client = await self._get_client()
        key = self._make_key(session_id)
        await client.delete(key)

    async def exists(self, session_id: str) -> bool:
        """Check if session exists."""
        client = await self._get_client()
        key = self._make_key(session_id)
        result = await client.exists(key)
        return bool(result)

    async def close(self) -> None:
        """Close Redis connection."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None


def get_session_store() -> SessionStore:
    """Factory function to create appropriate session store based on configuration.

    Environment variables:
        VALERIE_SESSION_STORE: Type of store ('memory' or 'redis'), default: 'memory'
        VALERIE_SESSION_REDIS_URL: Redis URL, default: 'redis://localhost:6379'
        VALERIE_SESSION_PREFIX: Key prefix, default: 'valerie:session:'

    Returns:
        Configured session store instance
    """
    store_type = os.getenv("VALERIE_SESSION_STORE", "memory").lower()

    if store_type == "redis":
        redis_url = os.getenv("VALERIE_SESSION_REDIS_URL", "redis://localhost:6379")
        prefix = os.getenv("VALERIE_SESSION_PREFIX", "valerie:session:")
        return RedisSessionStore(redis_url=redis_url, prefix=prefix)
    else:
        return InMemorySessionStore()


def get_default_ttl() -> int:
    """Get default TTL from environment.

    Environment variables:
        VALERIE_SESSION_TTL: Session TTL in seconds, default: 3600

    Returns:
        TTL in seconds
    """
    return int(os.getenv("VALERIE_SESSION_TTL", "3600"))
