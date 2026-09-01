from unittest.mock import patch

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


def test_run_endpoint_accepts_uploaded_files():
    project = {
        "id": "ia_quarteto",
        "name": "Teste",
        "project_path": "../IA_QUARTETO",
        "required_files": [
            {"id": "prefeitura", "accepted_extensions": ["csv"]},
            {"id": "fs10n", "accepted_extensions": ["xlsx"]},
            {"id": "zsd008", "accepted_extensions": ["xlsx"]},
        ],
        "outputs": ["Check_Faturamento.xlsx", "Report_Faturamento.xlsx"],
    }

    client = TestClient(app)

    with patch("api.app.load_projects", return_value={"ia_quarteto": project}):
        with patch("api.app.UploadMapper.map_uploaded_files", return_value={
            "prefeitura": {"file_name": "a.csv"},
            "fs10n": {"file_name": "b.xlsx"},
        }):
            with patch("api.app.Executor.run") as run_mock:
                with patch(
                    "api.app.OutputValidator.validate",
                    return_value={
                        "found": [
                            {"name": "Check_Faturamento.xlsx"},
                            {"name": "Report_Faturamento.xlsx"},
                        ],
                        "missing": [],
                    },
                ):
                    response = client.post(
                        "/projects/ia_quarteto/run",
                        files=[
                            ("files", ("prefeitura.csv", b"col1,col2\n1,2\n", "text/csv")),
                            ("files", ("fs10n.xlsx", b"123", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")),
                        ],
                    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "success"
    run_mock.assert_called_once()
