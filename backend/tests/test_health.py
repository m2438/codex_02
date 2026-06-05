from fastapi.testclient import TestClient

from app.main import app, settings


client = TestClient(app)


def test_health_endpoint_returns_service_status() -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "app": settings.app_name,
        "mode": settings.ai_mode,
        "database": "sqlite",
    }


def test_config_endpoint_returns_safe_frontend_config() -> None:
    response = client.get("/api/config")

    assert response.status_code == 200
    assert response.json() == {
        "appName": settings.app_name,
        "aiMode": settings.ai_mode,
        "language": "ja",
    }
