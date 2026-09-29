from fastapi.testclient import TestClient

from app.main import app


def test_health() -> None:
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_root_points_to_docs_and_health() -> None:
    with TestClient(app) as client:
        response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {
        "name": "AI Sales CRM Assistant",
        "docs": "/docs",
        "health": "/health",
    }
