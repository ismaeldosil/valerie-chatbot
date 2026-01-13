"""Example usage of session store implementations.

This demonstrates how to use both InMemorySessionStore and RedisSessionStore
for managing chatbot session state.
"""

import asyncio
import os

from valerie.infrastructure import (
    InMemorySessionStore,
    RedisSessionStore,
    get_default_ttl,
    get_session_store,
)


async def example_in_memory_store():
    """Example using in-memory session store."""
    print("=== In-Memory Session Store Example ===\n")

    store = InMemorySessionStore()

    # Save a session
    session_id = "user-123-session"
    state = {
        "user_id": "user-123",
        "conversation_step": 1,
        "intent": "supplier_search",
        "context": {
            "industry": "aerospace",
            "location": "USA",
        },
    }

    ttl = get_default_ttl()
    await store.save(session_id, state, ttl)
    print(f"Saved session: {session_id}")

    # Load the session
    loaded_state = await store.load(session_id)
    print(f"Loaded state: {loaded_state}\n")

    # Update the session
    if loaded_state:
        loaded_state["conversation_step"] = 2
        loaded_state["last_query"] = "Find suppliers in California"
        await store.save(session_id, loaded_state, ttl)
        print(f"Updated session step to: {loaded_state['conversation_step']}\n")

    # Check if session exists
    exists = await store.exists(session_id)
    print(f"Session exists: {exists}\n")

    # Delete the session
    await store.delete(session_id)
    print(f"Deleted session: {session_id}")

    # Verify deletion
    exists_after_delete = await store.exists(session_id)
    print(f"Session exists after delete: {exists_after_delete}\n")


async def example_redis_store():
    """Example using Redis session store.

    Note: Requires Redis server running at redis://localhost:6379
    """
    print("=== Redis Session Store Example ===\n")

    # Create Redis store
    store = RedisSessionStore(
        redis_url="redis://localhost:6379",
        prefix="example:session:",
    )

    try:
        # Save a session
        session_id = "redis-session-456"
        state = {
            "user_id": "user-456",
            "conversation_step": 1,
            "suppliers_viewed": ["SUP-001", "SUP-002"],
            "preferences": {
                "risk_tolerance": "low",
                "certifications_required": ["ISO9001", "AS9100"],
            },
        }

        await store.save(session_id, state, ttl=7200)  # 2 hour TTL
        print(f"Saved session to Redis: {session_id}")

        # Load the session
        loaded_state = await store.load(session_id)
        print(f"Loaded state: {loaded_state}\n")

        # Update the session
        if loaded_state:
            loaded_state["conversation_step"] = 2
            loaded_state["suppliers_viewed"].append("SUP-003")
            await store.save(session_id, loaded_state, ttl=7200)
            print(f"Updated session: {loaded_state}\n")

        # Check existence
        exists = await store.exists(session_id)
        print(f"Session exists in Redis: {exists}\n")

        # Cleanup
        await store.delete(session_id)
        print(f"Deleted session: {session_id}")

    finally:
        # Close Redis connection
        await store.close()
        print("Closed Redis connection\n")


async def example_factory_function():
    """Example using factory function with environment variables."""
    print("=== Factory Function Example ===\n")

    # Set environment variables to configure store type
    os.environ["VALERIE_SESSION_STORE"] = "memory"
    os.environ["VALERIE_SESSION_TTL"] = "1800"  # 30 minutes

    # Get store based on configuration
    store = get_session_store()
    print(f"Created store type: {type(store).__name__}")
    print(f"Default TTL: {get_default_ttl()} seconds\n")

    # Use the store
    session_id = "factory-session"
    state = {"step": 1, "data": "example"}

    await store.save(session_id, state)
    loaded = await store.load(session_id)
    print(f"Loaded state: {loaded}\n")

    await store.delete(session_id)


async def example_multiple_sessions():
    """Example managing multiple concurrent sessions."""
    print("=== Multiple Sessions Example ===\n")

    store = InMemorySessionStore()

    # Create multiple sessions
    sessions = {
        "session-alice": {
            "user_id": "alice",
            "step": 1,
            "query": "aerospace suppliers",
        },
        "session-bob": {
            "user_id": "bob",
            "step": 2,
            "query": "defense contractors",
        },
        "session-charlie": {
            "user_id": "charlie",
            "step": 1,
            "query": "ITAR compliant suppliers",
        },
    }

    # Save all sessions concurrently
    await asyncio.gather(
        *[store.save(sid, state) for sid, state in sessions.items()]
    )
    print(f"Saved {len(sessions)} sessions concurrently\n")

    # Load all sessions concurrently
    loaded_states = await asyncio.gather(
        *[store.load(sid) for sid in sessions.keys()]
    )

    for session_id, state in zip(sessions.keys(), loaded_states):
        print(f"{session_id}: {state}")

    print()

    # Cleanup all sessions
    await asyncio.gather(*[store.delete(sid) for sid in sessions.keys()])
    print(f"Deleted all {len(sessions)} sessions\n")


async def main():
    """Run all examples."""
    print("Session Store Examples\n" + "=" * 50 + "\n")

    # Run in-memory example
    await example_in_memory_store()

    # Run factory function example
    await example_factory_function()

    # Run multiple sessions example
    await example_multiple_sessions()

    # Run Redis example (commented out by default)
    # Uncomment if you have Redis running
    # await example_redis_store()

    print("=" * 50)
    print("All examples completed!")


if __name__ == "__main__":
    asyncio.run(main())
