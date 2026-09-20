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


def test_health_service_reports_detailed_status(tmp_path: Path):
    project_dir = tmp_path / "external_project"
    project_dir.mkdir()
    (project_dir / "main.py").write_text("print('ok')\n", encoding="utf-8")
    (project_dir / "data").mkdir()
    (project_dir / "data" / "output").mkdir()
    (project_dir / "data" / "output" / "result.xlsx").write_bytes(b"ok")

    manifest_dir = tmp_path / "manifests"
    manifest_dir.mkdir()
    manifest_yaml = """
id: demo
name: Demo
category: test
description: Demo manifest
project_path: ../external_project
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

    with patch("core.health_service.MANIFESTS_DIR", manifest_dir), patch(
        "core.health_service.BASE_DIR", tmp_path
    ):
        result = HealthService.diagnose_details()

    assert result["status"] in {"ok", "warning", "error"}
    assert "python" in result
    assert "manifests" in result
    assert "sqlite" in result
