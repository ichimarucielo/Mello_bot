import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from core.exceptions import TimeoutExecutionError
from core.executor import Executor
from core.health_service import HealthService


def make_manifest(project_path, script="main.py", timeout_seconds=1800):
    manifest = MagicMock()
    manifest.name = "Teste"
    manifest.project_path = str(project_path)
    manifest.entrypoint.script = script
    manifest.timeout_seconds = timeout_seconds
    required_file = MagicMock()
    required_file.id = "input"
    required_file.cli_argument = "--input"
    manifest.required_files = [required_file]
    manifest.outputs = ["result.xlsx"]
    return manifest


def test_executor_raises_timeout_execution_error(tmp_path: Path):
    project_path = tmp_path
    (project_path / "main.py").touch()
    input_path = tmp_path / "input.csv"
    input_path.touch()
    manifest = make_manifest(".", timeout_seconds=1)

    with patch("core.executor.load_manifest", return_value=manifest), patch(
        "core.executor.subprocess.run",
        side_effect=subprocess.TimeoutExpired(cmd="python", timeout=1),
    ), patch("core.executor.BASE_DIR", project_path):
        with pytest.raises(TimeoutExecutionError):
            Executor.run("demo", {"input": str(input_path)})


def test_health_service_reports_detailed_status(tmp_path: Path, monkeypatch):
    project_dir = tmp_path / "external_project"
    project_dir.mkdir()
    (project_dir / "main.py").write_text("print('ok')\n", encoding="utf-8")
    (project_dir / "data").mkdir()
    (project_dir / "data" / "output").mkdir()

    manifest_dir = tmp_path / "manifests"
    manifest_dir.mkdir()
    manifest_yaml = """
id: demo
name: Demo
category: test
description: Demo manifest
project_path: external_project
entrypoint:
  script: main.py
required_files:
  - id: input
    display_name: Input
    cli_argument: --input
    accepted_extensions: [csv]
    required_columns: [coluna]
outputs:
  - result.xlsx
"""
    (manifest_dir / "demo.yaml").write_text(manifest_yaml, encoding="utf-8")
    broken_yaml = manifest_yaml.replace("id: demo", "id: broken").replace(
        "name: Demo", "name: Broken"
    ).replace("project_path: external_project", "project_path: missing_project")
    (manifest_dir / "broken.yaml").write_text(broken_yaml, encoding="utf-8")
    storage_dir = tmp_path / "storage"
    storage_dir.mkdir()

    monkeypatch.setattr(
        "core.health_service.ManifestGenerator.list_manifest_files",
        lambda: sorted(manifest_dir.glob("*.yaml")),
    )
    monkeypatch.setattr("core.manifest_loader.MANIFESTS_PATH", manifest_dir)
    monkeypatch.setattr("core.health_service.MANIFESTS_DIR", manifest_dir)
    monkeypatch.setattr("core.health_service.BASE_DIR", tmp_path)
    monkeypatch.setattr(
        "core.health_service.DATABASE_PATH",
        storage_dir / "mello.db",
    )

    result = HealthService.diagnose_details()

    assert result["status"] == "warning"
    assert "python" in result
    assert "manifests" in result
    assert "sqlite" in result
    assert result["manifests"]["valid"] == 2
    assert result["manifests"]["healthy_projects"] == 1
    assert result["manifests"]["projects_needing_attention"] == 1
    project_status = {item["id"]: item for item in result["projects"]}
    assert project_status["demo"]["healthy"] is True
    assert project_status["broken"]["healthy"] is False
    assert "project_path_missing:broken" in result["problems"]
    outputs = {item["project_id"]: item for item in result["outputs"]}
    assert outputs["demo"]["configured"] is True
    assert outputs["demo"]["generated"] == []
    assert outputs["demo"]["missing"] == ["result.xlsx"]


def test_health_service_distinguishes_yaml_validity_from_project_health(
    tmp_path: Path,
    monkeypatch,
):
    project_dir = tmp_path / "projects" / "healthy"
    project_dir.mkdir(parents=True)
    (project_dir / "main.py").write_text("pass\n", encoding="utf-8")
    manifest_dir = tmp_path / "manifests"
    manifest_dir.mkdir()
    manifest_yaml = """
id: healthy
name: Healthy
category: test
description: Test manifest
project_path: projects/healthy
entrypoint:
  script: main.py
required_files: []
outputs: [result.xlsx]
"""
    healthy_manifest = manifest_dir / "healthy.yaml"
    healthy_manifest.write_text(manifest_yaml, encoding="utf-8")
    missing_project_yaml = manifest_yaml.replace(
        "id: healthy", "id: missing_project"
    ).replace(
        "name: Healthy", "name: Missing project"
    ).replace(
        "project_path: projects/healthy", "project_path: projects/missing"
    )
    missing_project_manifest = manifest_dir / "missing_project.yaml"
    missing_project_manifest.write_text(missing_project_yaml, encoding="utf-8")

    monkeypatch.setattr(
        "core.health_service.ManifestGenerator.list_manifest_files",
        lambda: [healthy_manifest, missing_project_manifest],
    )
    monkeypatch.setattr("core.health_service.BASE_DIR", tmp_path)

    result = HealthService.diagnose()

    assert result["manifest_count"] == 2
    assert result["valid_manifests"] == 2
    assert result["healthy_projects"] == 1
    assert result["unhealthy_projects"] == 1
    assert result["outputs_configured"] == 2
    assert result["accessible_outputs"] == 0
    project_health = {item["id"]: item for item in result["details"]}
    assert project_health["healthy"]["healthy"] is True
    assert project_health["healthy"]["outputs"] is False
    assert project_health["missing_project"]["healthy"] is False
