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


def test_api_detection_rules(client):
    # GET rules
    response = client.get("/api/security/rules")
    assert response.status_code == 200
    rules = response.json()
    assert isinstance(rules, list)
    assert len(rules) >= 5

    # POST update rule threshold
    update_res = client.post(
        "/api/security/rules/RULE-AUTH-001",
        json={"threshold": 7, "window_seconds": 150}
    )
    assert update_res.status_code == 200
    updated_rule = update_res.json()
    assert updated_rule["threshold"] == 7
    assert updated_rule["window_seconds"] == 150


def test_api_auth_events(client):
    response = client.get("/api/security/auth-events?limit=5")
    assert response.status_code == 200
    events = response.json()
    assert isinstance(events, list)
    if events:
        assert "event_type" in events[0]
        assert "severity" in events[0]


def test_api_system_integrity(client):
    response = client.get("/api/security/integrity")
    assert response.status_code == 200
    items = response.json()
    assert isinstance(items, list)
    assert len(items) >= 1
    assert "sha256" in items[0]
    assert "status" in items[0]


def test_api_sanitize(client):
    response = client.post(
        "/api/security/sanitize",
        json={"content": "POST /login?password=mysecretpassword123 HTTP/1.1"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "mysecretpassword123" not in data["sanitized_content"]
    assert "password=[REDACTED]" in data["sanitized_content"]
