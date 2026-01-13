"""Railway deployment runner for Streamlit UI."""

import os
import subprocess
import sys

port = os.environ.get("PORT", "8501")

print("=" * 60)
print("Valerie Chatbot UI Startup")
print("=" * 60)
print(f"Python version: {sys.version}")
print(f"PORT: {port}")
print(f"VALERIE_ANTHROPIC_API_KEY: {'set' if os.environ.get('VALERIE_ANTHROPIC_API_KEY') else 'not set'}")
print("=" * 60)

# Run streamlit
cmd = [
    "streamlit",
    "run",
    "demo/app.py",
    "--server.port",
    port,
    "--server.address",
    "0.0.0.0",
    "--server.headless",
    "true",
    "--browser.gatherUsageStats",
    "false",
]

print(f"Running: {' '.join(cmd)}")
subprocess.run(cmd)
