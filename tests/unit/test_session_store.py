"""Tests for session store implementations."""

import asyncio
import json
import os
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from valerie.infrastructure.session_store import (
    InMemorySessionStore,
    RedisSessionStore,
    SessionStore,
    get_default_ttl,
    get_session_store,
)


class TestSessionStoreInterface:
    """Tests for SessionStore abstract interface."""

    def test_cannot_instantiate_abstract_class(self):
        """Test that SessionStore cannot be instantiated directly."""
        with pytest.raises(TypeError):
            SessionStore()  # type: ignore


class TestInMemorySessionStore:
    """Tests for InMemorySessionStore implementation."""

    @pytest.fixture
    def store(self) -> InMemorySessionStore:
        """Create a fresh in-memory store for each test."""
        return InMemorySessionStore()

    @pytest.mark.asyncio
    async def test_save_and_load(self, store: InMemorySessionStore):
        """Test saving and loading session state."""
        session_id = "test-session-1"
        state = {"user_id": "user-123", "step": 1, "data": {"key": "value"}}

        await store.save(session_id, state, ttl=3600)
        loaded = await store.load(session_id)

        assert loaded == state

    @pytest.mark.asyncio
    async def test_load_nonexistent_session(self, store: InMemorySessionStore):
        """Test loading a session that doesn't exist."""
        loaded = await store.load("nonexistent")
        assert loaded is None

    @pytest.mark.asyncio
    async def test_save_overwrites_existing(self, store: InMemorySessionStore):
        """Test that saving overwrites existing session."""
        session_id = "test-session-2"
        state1 = {"step": 1}
        state2 = {"step": 2}

        await store.save(session_id, state1)
        await store.save(session_id, state2)

        loaded = await store.load(session_id)
        assert loaded == state2

    @pytest.mark.asyncio
    async def test_delete_session(self, store: InMemorySessionStore):
        """Test deleting a session."""
        session_id = "test-session-3"
        state = {"data": "test"}

        await store.save(session_id, state)
        assert await store.exists(session_id)

        await store.delete(session_id)
        assert not await store.exists(session_id)

        loaded = await store.load(session_id)
        assert loaded is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_session(self, store: InMemorySessionStore):
        """Test deleting a session that doesn't exist."""
        await store.delete("nonexistent")
        # Should not raise an error

    @pytest.mark.asyncio
    async def test_exists(self, store: InMemorySessionStore):
        """Test checking if session exists."""
        session_id = "test-session-4"

        assert not await store.exists(session_id)

        await store.save(session_id, {"data": "test"})
        assert await store.exists(session_id)

        await store.delete(session_id)
        assert not await store.exists(session_id)

    @pytest.mark.asyncio
    async def test_ttl_expiration(self, store: InMemorySessionStore):
        """Test that sessions expire after TTL."""
        session_id = "test-session-5"
        state = {"data": "test"}

        # Save with 1 second TTL
        await store.save(session_id, state, ttl=1)
        assert await store.exists(session_id)

        # Wait for expiration
        await asyncio.sleep(1.1)

        # Session should be expired
        assert not await store.exists(session_id)
        loaded = await store.load(session_id)
        assert loaded is None

    @pytest.mark.asyncio
    async def test_cleanup_expired_sessions(self, store: InMemorySessionStore):
        """Test that expired sessions are cleaned up."""
        # Add expired session
        session_id_expired = "expired-session"
        store._store[session_id_expired] = ({"data": "old"}, time.time() - 100)

        # Add valid session
        session_id_valid = "valid-session"
        await store.save(session_id_valid, {"data": "new"}, ttl=3600)

        # Cleanup should be triggered on save
        assert session_id_expired not in store._store
        assert session_id_valid in store._store

    @pytest.mark.asyncio
    async def test_multiple_sessions(self, store: InMemorySessionStore):
        """Test managing multiple sessions."""
        sessions = {
            "session-1": {"user": "alice", "count": 1},
            "session-2": {"user": "bob", "count": 2},
            "session-3": {"user": "charlie", "count": 3},
        }

        # Save all sessions
        for session_id, state in sessions.items():
            await store.save(session_id, state)

        # Verify all sessions
        for session_id, expected_state in sessions.items():
            loaded = await store.load(session_id)
            assert loaded == expected_state

        # Delete one session
        await store.delete("session-2")

        # Verify remaining sessions
        assert await store.exists("session-1")
        assert not await store.exists("session-2")
        assert await store.exists("session-3")

    @pytest.mark.asyncio
    async def test_complex_state_serialization(self, store: InMemorySessionStore):
        """Test storing complex state objects."""
        session_id = "complex-session"
        complex_state = {
            "nested": {"deep": {"value": 123}},
            "list": [1, 2, 3, {"key": "value"}],
            "boolean": True,
            "null": None,
            "float": 3.14,
        }

        await store.save(session_id, complex_state)
        loaded = await store.load(session_id)

        assert loaded == complex_state


class TestRedisSessionStore:
    """Tests for RedisSessionStore implementation."""

    @pytest.fixture
    def mock_redis(self) -> MagicMock:
        """Create a mock Redis client."""
        mock = MagicMock()
        mock.setex = AsyncMock()
        mock.get = AsyncMock()
        mock.delete = AsyncMock()
        mock.exists = AsyncMock()
        mock.aclose = AsyncMock()
        return mock

    @pytest.fixture
    def store(self, mock_redis: MagicMock) -> RedisSessionStore:
        """Create a RedisSessionStore with mocked client."""
        store = RedisSessionStore(redis_url="redis://localhost:6379", prefix="test:session:")

        # Directly inject the mock client
        store._client = mock_redis

        return store

    @pytest.mark.asyncio
    async def test_save(self, store: RedisSessionStore, mock_redis: MagicMock):
        """Test saving session state to Redis."""
        session_id = "test-session-1"
        state = {"user_id": "user-123", "step": 1}
        ttl = 3600

        await store.save(session_id, state, ttl)

        mock_redis.setex.assert_called_once_with(
            "test:session:test-session-1", ttl, json.dumps(state)
        )

    @pytest.mark.asyncio
    async def test_load_existing_session(self, store: RedisSessionStore, mock_redis: MagicMock):
        """Test loading existing session from Redis."""
        session_id = "test-session-2"
        state = {"data": "test"}

        mock_redis.get.return_value = json.dumps(state)

        loaded = await store.load(session_id)

        assert loaded == state
        mock_redis.get.assert_called_once_with("test:session:test-session-2")

    @pytest.mark.asyncio
    async def test_load_nonexistent_session(self, store: RedisSessionStore, mock_redis: MagicMock):
        """Test loading session that doesn't exist."""
        mock_redis.get.return_value = None

        loaded = await store.load("nonexistent")

        assert loaded is None

    @pytest.mark.asyncio
    async def test_delete(self, store: RedisSessionStore, mock_redis: MagicMock):
        """Test deleting session from Redis."""
        session_id = "test-session-3"

        await store.delete(session_id)

        mock_redis.delete.assert_called_once_with("test:session:test-session-3")

    @pytest.mark.asyncio
    async def test_exists_true(self, store: RedisSessionStore, mock_redis: MagicMock):
        """Test checking if session exists (True case)."""
        mock_redis.exists.return_value = 1

        exists = await store.exists("test-session-4")

        assert exists is True
        mock_redis.exists.assert_called_once_with("test:session:test-session-4")

    @pytest.mark.asyncio
    async def test_exists_false(self, store: RedisSessionStore, mock_redis: MagicMock):
        """Test checking if session exists (False case)."""
        mock_redis.exists.return_value = 0

        exists = await store.exists("nonexistent")

        assert exists is False

    @pytest.mark.asyncio
    async def test_close(self, store: RedisSessionStore, mock_redis: MagicMock):
        """Test closing Redis connection."""
        await store.close()

        mock_redis.aclose.assert_called_once()
        assert store._client is None

    @pytest.mark.asyncio
    async def test_make_key(self):
        """Test key prefix functionality."""
        store = RedisSessionStore(prefix="custom:prefix:")

        key = store._make_key("session-id")

        assert key == "custom:prefix:session-id"

    @pytest.mark.asyncio
    async def test_complex_state_serialization(
        self, store: RedisSessionStore, mock_redis: MagicMock
    ):
        """Test JSON serialization of complex state."""
        complex_state = {
            "nested": {"deep": {"value": 123}},
            "list": [1, 2, 3],
            "boolean": True,
            "null": None,
        }

        mock_redis.get.return_value = json.dumps(complex_state)

        loaded = await store.load("session-id")

        assert loaded == complex_state

    @pytest.mark.asyncio
    async def test_client_reuse(self, store: RedisSessionStore, mock_redis: MagicMock):
        """Test that Redis client is reused across operations."""
        await store.save("session-1", {"data": "1"})
        await store.save("session-2", {"data": "2"})

        # Client should be created only once
        assert store._client is mock_redis


class TestGetSessionStore:
    """Tests for get_session_store factory function."""

    def test_default_memory_store(self):
        """Test that memory store is default."""
        with patch.dict(os.environ, {}, clear=True):
            store = get_session_store()
            assert isinstance(store, InMemorySessionStore)

    def test_explicit_memory_store(self):
        """Test explicitly requesting memory store."""
        with patch.dict(os.environ, {"VALERIE_SESSION_STORE": "memory"}):
            store = get_session_store()
            assert isinstance(store, InMemorySessionStore)

    def test_redis_store(self):
        """Test creating Redis store."""
        with patch.dict(os.environ, {"VALERIE_SESSION_STORE": "redis"}):
            store = get_session_store()
            assert isinstance(store, RedisSessionStore)
            assert store.redis_url == "redis://localhost:6379"
            assert store.prefix == "valerie:session:"

    def test_redis_store_custom_url(self):
        """Test creating Redis store with custom URL."""
        with patch.dict(
            os.environ,
            {
                "VALERIE_SESSION_STORE": "redis",
                "VALERIE_SESSION_REDIS_URL": "redis://custom:6380",
            },
        ):
            store = get_session_store()
            assert isinstance(store, RedisSessionStore)
            assert store.redis_url == "redis://custom:6380"

    def test_redis_store_custom_prefix(self):
        """Test creating Redis store with custom prefix."""
        with patch.dict(
            os.environ,
            {
                "VALERIE_SESSION_STORE": "redis",
                "VALERIE_SESSION_PREFIX": "custom:prefix:",
            },
        ):
            store = get_session_store()
            assert isinstance(store, RedisSessionStore)
            assert store.prefix == "custom:prefix:"

    def test_case_insensitive_store_type(self):
        """Test that store type is case insensitive."""
        with patch.dict(os.environ, {"VALERIE_SESSION_STORE": "REDIS"}):
            store = get_session_store()
            assert isinstance(store, RedisSessionStore)

        with patch.dict(os.environ, {"VALERIE_SESSION_STORE": "Memory"}):
            store = get_session_store()
            assert isinstance(store, InMemorySessionStore)


class TestGetDefaultTTL:
    """Tests for get_default_ttl helper function."""

    def test_default_ttl(self):
        """Test default TTL value."""
        with patch.dict(os.environ, {}, clear=True):
            ttl = get_default_ttl()
            assert ttl == 3600

    def test_custom_ttl(self):
        """Test custom TTL from environment."""
        with patch.dict(os.environ, {"VALERIE_SESSION_TTL": "7200"}):
            ttl = get_default_ttl()
            assert ttl == 7200

    def test_ttl_type_conversion(self):
        """Test that TTL is converted to int."""
        with patch.dict(os.environ, {"VALERIE_SESSION_TTL": "1800"}):
            ttl = get_default_ttl()
            assert isinstance(ttl, int)
            assert ttl == 1800


class TestSessionStoreIntegration:
    """Integration tests for session stores."""

    @pytest.mark.asyncio
    async def test_in_memory_workflow(self):
        """Test complete workflow with in-memory store."""
        store = InMemorySessionStore()

        # Create session
        session_id = "integration-test"
        initial_state = {"step": 1, "user": "alice"}

        await store.save(session_id, initial_state)
        assert await store.exists(session_id)

        # Load and modify
        loaded = await store.load(session_id)
        assert loaded is not None
        loaded["step"] = 2
        loaded["data"] = "updated"

        # Save updated state
        await store.save(session_id, loaded)

        # Verify update
        final = await store.load(session_id)
        assert final == {"step": 2, "user": "alice", "data": "updated"}

        # Cleanup
        await store.delete(session_id)
        assert not await store.exists(session_id)

    @pytest.mark.asyncio
    async def test_concurrent_sessions(self):
        """Test handling concurrent sessions."""
        store = InMemorySessionStore()

        # Create multiple sessions concurrently
        sessions = [
            ("session-1", {"user": "alice"}),
            ("session-2", {"user": "bob"}),
            ("session-3", {"user": "charlie"}),
        ]

        # Save all concurrently
        await asyncio.gather(*[store.save(sid, state) for sid, state in sessions])

        # Load all concurrently
        results = await asyncio.gather(*[store.load(sid) for sid, _ in sessions])

        # Verify all results
        for (_, expected_state), actual_state in zip(sessions, results):
            assert actual_state == expected_state

        # Cleanup all concurrently
        await asyncio.gather(*[store.delete(sid) for sid, _ in sessions])
