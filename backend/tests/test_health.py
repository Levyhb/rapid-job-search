from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_ready_checks_both_services():
    with (
        patch("app.api.health.engine.connect", return_value=MagicMock()),
        patch("app.api.health.Redis.from_url", return_value=MagicMock()),
    ):
        response = client.get("/health/ready")
    assert response.status_code == 200
    assert response.json()["services"] == {"postgres": "ok", "redis": "ok"}


def test_failed_database_is_not_reported_as_healthy():
    with (
        patch("app.api.health.engine.connect", side_effect=ConnectionError("offline")),
        patch("app.api.health.Redis.from_url", return_value=MagicMock()),
    ):
        response = client.get("/health/ready")
    assert response.status_code == 503
    assert response.json()["services"] == {"postgres": "unavailable", "redis": "ok"}


def test_health_does_not_require_infrastructure():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_allowed_frontend_can_access_api():
    response = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_unknown_origin_is_not_allowed():
    response = client.options(
        "/health",
        headers={
            "Origin": "http://example.invalid",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers
