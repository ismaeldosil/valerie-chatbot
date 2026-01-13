#!/usr/bin/env python3
"""
Simple run script to test the chatbot without full installation.

Usage:
    python3 scripts/run.py test-graph
    python3 scripts/run.py chat
    python3 scripts/run.py config
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Now import and run
from valerie.cli import app

if __name__ == "__main__":
    app()
