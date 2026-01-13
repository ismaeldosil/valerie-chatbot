"""Tests for supplier search endpoints."""


class TestSupplierSearchEndpoints:
    """Tests for /api/v1/suppliers/search endpoint."""

    def test_search_by_process(self, client):
        """Test searching suppliers by process."""
        response = client.post("/api/v1/suppliers/search", json={"processes": ["heat_treatment"]})
        assert response.status_code == 200

        data = response.json()
        assert "suppliers" in data
        assert "total_count" in data
        assert "search_criteria" in data
        assert isinstance(data["suppliers"], list)

    def test_search_returns_supplier_details(self, client):
        """Test search returns complete supplier details."""
        response = client.post("/api/v1/suppliers/search", json={"processes": ["heat_treatment"]})
        data = response.json()

        if data["total_count"] > 0:
            supplier = data["suppliers"][0]
            assert "id" in supplier
            assert "name" in supplier
            assert "location" in supplier
            assert "processes" in supplier
            assert "certifications" in supplier
            assert "quality_score" in supplier
            assert "delivery_score" in supplier
            assert "capacity_available" in supplier
            assert "lead_time_days" in supplier

    def test_search_by_multiple_processes(self, client):
        """Test searching by multiple processes."""
        response = client.post(
            "/api/v1/suppliers/search", json={"processes": ["heat_treatment", "anodizing"]}
        )
        assert response.status_code == 200

        data = response.json()
        assert data["search_criteria"]["processes"] == ["heat_treatment", "anodizing"]

    def test_search_with_certification_filter(self, client):
        """Test filtering by certification."""
        response = client.post(
            "/api/v1/suppliers/search",
            json={"processes": ["heat_treatment"], "certifications": ["Nadcap"]},
        )
        assert response.status_code == 200

        data = response.json()
        # All returned suppliers should have Nadcap
        for supplier in data["suppliers"]:
            cert_names = " ".join([c["name"] for c in supplier["certifications"]])
            assert "Nadcap" in cert_names

    def test_search_with_quality_filter(self, client):
        """Test filtering by minimum quality score."""
        response = client.post(
            "/api/v1/suppliers/search",
            json={"processes": ["heat_treatment"], "min_quality_score": 0.95},
        )
        assert response.status_code == 200

        data = response.json()
        # All returned suppliers should meet quality threshold
        for supplier in data["suppliers"]:
            assert supplier["quality_score"] >= 0.95

    def test_search_no_results(self, client):
        """Test search with no matching results."""
        response = client.post(
            "/api/v1/suppliers/search", json={"processes": ["nonexistent_process"]}
        )
        assert response.status_code == 200

        data = response.json()
        assert data["total_count"] == 0
        assert data["suppliers"] == []

    def test_search_empty_processes_rejected(self, client):
        """Test empty processes list is rejected."""
        response = client.post("/api/v1/suppliers/search", json={"processes": []})
        assert response.status_code == 422  # Validation error

    def test_search_invalid_quality_score(self, client):
        """Test invalid quality score is rejected."""
        response = client.post(
            "/api/v1/suppliers/search",
            json={
                "processes": ["heat_treatment"],
                "min_quality_score": 1.5,  # Invalid, must be 0-1
            },
        )
        assert response.status_code == 422

    def test_search_criteria_in_response(self, client, sample_supplier_search):
        """Test search criteria is included in response."""
        response = client.post("/api/v1/suppliers/search", json=sample_supplier_search)
        data = response.json()

        criteria = data["search_criteria"]
        assert criteria["processes"] == sample_supplier_search["processes"]
        assert criteria["certifications"] == sample_supplier_search["certifications"]
        assert criteria["min_quality_score"] == sample_supplier_search["min_quality_score"]
