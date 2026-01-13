"""Fixtures for API tests."""

import pytest
from fastapi.testclient import TestClient

from valerie.api.main import app


@pytest.fixture
def client():
    """Create a test client for the API."""
    with TestClient(app) as client:
        yield client


@pytest.fixture
def sample_chat_request():
    """Sample chat request payload."""
    return {"message": "Find heat treatment suppliers"}


@pytest.fixture
def sample_supplier_search():
    """Sample supplier search request."""
    return {"processes": ["heat_treatment"], "certifications": ["Nadcap"], "min_quality_score": 0.9}
