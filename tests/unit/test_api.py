"""Unit tests for LogShield FastAPI endpoints."""

import pytest
from fastapi.testclient import TestClient

from src.logshield.api.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_api_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data


def test_api_stats(client):
    response = client.get("/api/stats")
    assert response.status_code == 200
    data = response.json()
    assert data["total_requests"] in (199998, 200000)
    assert data["total_404"] == 43153
    assert data["error_rate"] == 21.58
    assert data["peak_failure_hour"] == 3


def test_api_traffic(client):
    response = client.get("/api/traffic")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 24


def test_api_errors(client):
    response = client.get("/api/errors")
    assert response.status_code == 200
    data = response.json()
    assert data["total_404_errors"] == 43153


def test_api_security(client):
    response = client.get("/api/security?limit=10")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) <= 10


def test_api_top_ips(client):
    response = client.get("/api/top-ips?limit=5")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) <= 5
