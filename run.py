"""Railway deployment runner - handles PORT environment variable."""

import os
import sys

print("=" * 60)
print("Valerie Chatbot Startup")
print("=" * 60)
print(f"Python version: {sys.version}")
print(f"PORT env: {os.environ.get('PORT', 'not set (using 8000)')}")
print(f"ANTHROPIC_API_KEY: {'set' if os.environ.get('ANTHROPIC_API_KEY') else 'not set'}")
print("=" * 60)

# Test imports before starting
print("Testing imports...")
try:
    print("  - Importing valerie package...")
    import valerie

    print("  - Importing valerie.api.main...")
    from valerie.api.main import app

    print("  - All imports successful!")
except Exception as e:
    print(f"  - IMPORT ERROR: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)

if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8000))
    print(f"\nStarting Uvicorn on 0.0.0.0:{port}")
    print("=" * 60)

    uvicorn.run(
        "valerie.api.main:app",
        host="0.0.0.0",
        port=port,
        log_level="info",
    )
