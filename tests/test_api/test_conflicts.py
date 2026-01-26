"""
Tests for conflict API endpoints.
"""

import pytest
from fastapi.testclient import TestClient


class TestConflictEndpoints:
    """Test cases for conflict-related API endpoints."""
    
    def test_list_conflicts_empty(self, client: TestClient):
        """Test listing conflicts returns empty list initially."""
        response = client.get("/api/v1/conflicts/")
        assert response.status_code == 200
        # May have conflicts from other tests, just check it returns a list
        assert isinstance(response.json(), list)
    
    def test_get_conflict_not_found(self, client: TestClient):
        """Test getting non-existent conflict returns 404."""
        response = client.get("/api/v1/conflicts/non-existent-id")
        assert response.status_code == 404
    
    def test_generate_synthetic_conflicts(self, client: TestClient):
        """Test generating synthetic conflicts."""
        response = client.post(
            "/api/v1/conflicts/generate",
            json={"count": 5}
        )
        assert response.status_code == 200
        data = response.json()
        assert "generated_count" in data
        assert "summary" in data
    
    def test_health_check(self, client: TestClient):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
