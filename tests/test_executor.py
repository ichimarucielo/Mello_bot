from pathlib import Path
from unittest.mock import MagicMock, patch

from core.enums import ExecutionStatus
from core.executor import Executor


def make_manifest(project_path, script="main.py"):
    manifest = MagicMock()
    manifest.name = "Teste"
    manifest.project_path = str(project_path)
    manifest.entrypoint.script = script
    required_file = MagicMock()
    required_file.id = "input"
    required_file.cli_argument = "--input"
    manifest.required_files = [required_file]
    return manifest


def test_run_returns_success_result(tmp_path: Path):
    project_path = tmp_path
    (project_path / "main.py").touch()
    input_path = tmp_path / "input.csv"
    input_path.touch()
    manifest = make_manifest(".")

    with patch("core.executor.load_manifest", return_value=manifest), patch(
        "core.executor.subprocess.run"
    ) as run_process, patch("core.executor.BASE_DIR", project_path):
        run_process.return_value.returncode = 0
        run_process.return_value.stdout = "ok"
        run_process.return_value.stderr = ""

        result = Executor.run("demo", {"input": str(input_path)})

    assert result.project_id == "demo"
    assert result.status == ExecutionStatus.SUCCESS
    run_process.assert_called_once()
    assert "--input" in run_process.call_args.args[0]
    assert str(input_path) in run_process.call_args.args[0]


def test_run_returns_failed_result_with_process_output(tmp_path: Path):
    project_path = tmp_path
    (project_path / "main.py").touch()
    input_path = tmp_path / "input.csv"
    input_path.touch()
    manifest = make_manifest(".")

    with patch("core.executor.load_manifest", return_value=manifest), patch(
        "core.executor.subprocess.run"
    ) as run_process, patch("core.executor.BASE_DIR", project_path):
        run_process.return_value.returncode = 1
        run_process.return_value.stdout = "stdout error"
        run_process.return_value.stderr = "stderr error"

        result = Executor.run("demo", {"input": str(input_path)})

    assert result.status == ExecutionStatus.FAILED
    assert "stdout error" in result.error_message
    assert "stderr error" in result.error_message


def test_run_raises_when_entrypoint_does_not_exist(tmp_path: Path):
    manifest = make_manifest(tmp_path, "missing.py")
    manifest.project_path = str(tmp_path)

    with patch("core.executor.load_manifest", return_value=manifest):
        try:
            Executor.run("demo", {})
        except FileNotFoundError as error:
            assert "Entrypoint não encontrado" in str(error)
        else:
            raise AssertionError("Expected FileNotFoundError")
