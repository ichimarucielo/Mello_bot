from fastapi.testclient import TestClient

from api.app import app


def test_project_run_route_is_defined_once():
    routes = [
        route.path
        for route in app.router.routes
        if "projects" in route.path
    ]

    assert routes.count("/projects/{project_id}/run") == 1


def test_health_endpoint_returns_ok():
    client = TestClient(app)
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
