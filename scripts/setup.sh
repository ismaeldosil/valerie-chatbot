#!/bin/bash
# Setup script for Valerie Supplier Chatbot
# Run with: bash scripts/setup.sh

set -e

echo "==================================="
echo "Valerie Supplier Chatbot Setup"
echo "==================================="

# Check Python version
PYTHON_CMD=""
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
    echo "Found python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
    echo "Found python"
else
    echo "Error: Python not found. Please install Python 3.11+"
    exit 1
fi

# Check Python version is 3.11+
VERSION=$($PYTHON_CMD -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "Python version: $VERSION"

MAJOR=$(echo $VERSION | cut -d. -f1)
MINOR=$(echo $VERSION | cut -d. -f2)

if [ "$MAJOR" -lt 3 ] || ([ "$MAJOR" -eq 3 ] && [ "$MINOR" -lt 11 ]); then
    echo "Error: Python 3.11+ required. Found $VERSION"
    exit 1
fi

# Create virtual environment
echo ""
echo "Creating virtual environment..."
$PYTHON_CMD -m venv venv

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo ""
echo "Upgrading pip..."
pip install --upgrade pip

# Install package
echo ""
echo "Installing valerie-supplier-chatbot..."
pip install -e ".[dev]"

# Create .env if it doesn't exist
if [ ! -f .env ]; then
    echo ""
    echo "Creating .env from template..."
    cp .env.example .env
    echo "Please edit .env and add your VALERIE_ANTHROPIC_API_KEY"
fi

echo ""
echo "==================================="
echo "Setup Complete!"
echo "==================================="
echo ""
echo "To activate the environment:"
echo "  source venv/bin/activate"
echo ""
echo "To test the installation:"
echo "  valerie-chat test-graph"
echo ""
echo "To start the chatbot:"
echo "  valerie-chat chat"
echo ""
